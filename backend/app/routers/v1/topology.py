"""v1 topology API: graph read, document edits, SNMP/LLDP discovery.

Reads require `viewer`; writes and discovery runs require `operator`.
Every write appends an audit event.
"""
from __future__ import annotations

import csv
import io
import json
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ... import models, schemas
from ...config import get_settings
from ...db import get_session
from ...security import Principal, require_role
from ...services import snmp_discover, topology, topology_store
from ...services.audit import record_request_audit

router = APIRouter(tags=["topology"])

READ = Depends(require_role("viewer"))
WRITE = Depends(require_role("operator"))

_DOC_ID = 1
_INFRASTRUCTURE_TYPES = (
    "router", "switch", "ap", "server", "radio", "gateway", "firewall", "modem",
    "access_point", "controller", "repeater", "ont",
)


def _link_options():
    return (
        selectinload(models.NetworkLink.endpoints).selectinload(models.LinkEndpoint.device),
        selectinload(models.NetworkLink.endpoints).selectinload(models.LinkEndpoint.interface),
    )


async def _load_link(session: AsyncSession, link_id: int) -> models.NetworkLink | None:
    return await session.scalar(
        select(models.NetworkLink)
        .where(models.NetworkLink.id == link_id)
        .options(*_link_options())
    )


def _link_out(link: models.NetworkLink) -> schemas.NetworkLinkOut:
    endpoints = [
        schemas.LinkEndpointOut(
            id=endpoint.id,
            side=endpoint.side,
            device_id=endpoint.device_id,
            interface_id=endpoint.interface_id,
            device_label=(
                endpoint.device.label
                or endpoint.device.hostname
                or endpoint.device.vendor
                or endpoint.device.mac_address
            ),
            mac_address=endpoint.device.mac_address,
            interface_name=endpoint.interface.name if endpoint.interface else None,
        )
        for endpoint in link.endpoints
    ]
    return schemas.NetworkLinkOut(
        id=link.id,
        label=link.label,
        link_type=link.link_type,
        medium=link.medium,
        verification_status=link.verification_status,
        confidence=link.confidence,
        source=link.source,
        verification_evidence=link.verification_evidence,
        evidence=link.evidence or {},
        notes=link.notes,
        created_by=link.created_by,
        created_at=link.created_at,
        updated_at=link.updated_at,
        endpoints=endpoints,
    )


def _link_audit_state(link: models.NetworkLink) -> dict[str, Any]:
    return {
        "link_type": link.link_type,
        "medium": link.medium,
        "verification_status": link.verification_status,
        "confidence": link.confidence,
        "verification_evidence": link.verification_evidence,
        "endpoints": [
            {
                "side": endpoint.side,
                "device_id": endpoint.device_id,
                "interface_id": endpoint.interface_id,
            }
            for endpoint in sorted(link.endpoints, key=lambda item: item.side)
        ],
    }


async def _validate_endpoint_specs(
    session: AsyncSession, specs: list[schemas.LinkEndpointIn]
) -> None:
    if len(specs) != 2 or {spec.side for spec in specs} != {"A", "B"}:
        raise HTTPException(422, "a link must have exactly one A endpoint and one B endpoint")

    device_ids = {spec.device_id for spec in specs}
    devices = {
        device.id: device
        for device in await session.scalars(
            select(models.Device).where(models.Device.id.in_(device_ids))
        )
    }
    if devices.keys() != device_ids:
        raise HTTPException(422, "one or more endpoint devices do not exist")

    interface_ids = {spec.interface_id for spec in specs if spec.interface_id is not None}
    if interface_ids:
        interfaces = {
            interface.id: interface
            for interface in await session.scalars(
                select(models.DeviceInterface).where(models.DeviceInterface.id.in_(interface_ids))
            )
        }
        if interfaces.keys() != interface_ids:
            raise HTTPException(422, "one or more endpoint interfaces do not exist")
        for spec in specs:
            if (
                spec.interface_id is not None
                and interfaces[spec.interface_id].device_id != spec.device_id
            ):
                raise HTTPException(422, "an endpoint interface must belong to its selected device")


class TopologyDocumentIn(BaseModel):
    document: dict[str, Any]


class TopologyDocumentOut(BaseModel):
    document: dict[str, Any]
    updated_at: datetime | None = None


async def _audit(
    session: AsyncSession,
    request: Request,
    principal: Principal,
    action: str,
    entity_id: int | str,
    detail: dict[str, Any] | None = None,
    outcome: str = "success",
) -> None:
    await record_request_audit(
        session,
        request,
        actor=principal.username,
        role=principal.role,
        action=action,
        entity_type="topology",
        entity_id=entity_id,
        outcome=outcome,
        detail=detail,
        commit=True,
    )


@router.get("/topology/graph", dependencies=[READ], deprecated=True)
async def get_graph(
    include_clients: bool = Query(
        True,
        description="Include current device observations without inferring AP associations",
    ),
    client_limit: int = Query(80, ge=0, le=200),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Compatibility graph from the preserved legacy JSON topology document."""
    return await topology.build_topology(
        session, include_observations=include_clients, client_limit=client_limit
    )


@router.get("/topology/physical-graph", dependencies=[READ])
async def get_physical_graph(
    include_clients: bool = Query(
        False, description="Include unattached online client observations"
    ),
    client_limit: int = Query(80, ge=0, le=200),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Graph built only from inventoried devices and FK-backed link records."""
    infrastructure_filter = or_(
        models.Device.role.is_not(None), models.Device.type.in_(_INFRASTRUCTURE_TYPES)
    )
    topology_device_filter = or_(
        infrastructure_filter,
        models.Device.id.in_(select(models.LinkEndpoint.device_id)),
    )
    devices = list(
        await session.scalars(
            select(models.Device)
            .where(topology_device_filter)
            .options(
                selectinload(models.Device.location),
                selectinload(models.Device.model),
            )
            .order_by(models.Device.id)
            .limit(500)
        )
    )
    total_devices = int(
        await session.scalar(
            select(func.count()).select_from(models.Device).where(topology_device_filter)
        ) or 0
    )
    observed_clients: list[models.Device] = []
    if include_clients and client_limit:
        observed_clients = list(
            await session.scalars(
                select(models.Device)
                .where(
                    models.Device.online.is_(True),
                    models.Device.type.in_(("phone", "computer", "tablet", "endpoint")),
                    ~topology_device_filter,
                )
                .order_by(models.Device.last_seen.desc())
                .limit(client_limit)
            )
        )
    links = list(
        await session.scalars(
            select(models.NetworkLink).options(*_link_options()).order_by(models.NetworkLink.id)
        )
    )

    palette = ["#38bdf8", "#a78bfa", "#34d399", "#fbbf24", "#fb7185", "#22d3ee"]
    group_names = sorted(
        {device.location.name if device.location else "Unlocated" for device in devices}
    )
    group_ids = {name: f"location-{index}" for index, name in enumerate(group_names)}
    group_colors = {name: palette[index % len(palette)] for index, name in enumerate(group_names)}
    zones = [
        {"id": group_ids[name], "label": name, "color": group_colors[name]}
        for name in group_names
    ]
    if observed_clients:
        zones.append({"id": "observed-clients", "label": "Observed clients", "color": "#94a3b8"})

    nodes: list[dict[str, Any]] = []
    device_node_ids: set[int] = set()
    for device in devices:
        device_node_ids.add(device.id)
        label = device.label or device.hostname or device.vendor or device.mac_address
        group_name = device.location.name if device.location else "Unlocated"
        kind = device.role or device.type or "unknown"
        title = [label, f"Type: {device.type}", f"Condition: {device.condition}"]
        if device.model:
            title.append(f"Model: {device.model.vendor} {device.model.model}")
        if device.ip_address:
            title.append(f"IP: {device.ip_address}")
        nodes.append(
            {
                "id": f"device-{device.id}",
                "device_id": device.id,
                "label": label,
                "group": group_ids[group_name],
                "shape": "box" if kind in {"router", "switch", "gateway"} else "dot",
                "kind": kind,
                "title": "\n".join(title),
                "meta": {
                    "source": "device_inventory",
                    "device_id": device.id,
                    "mac": device.mac_address,
                    "ip": device.ip_address,
                    "vendor": device.vendor,
                    "hostname": device.hostname,
                    "role": device.role,
                    "condition": device.condition,
                    "identity_confidence": device.identity_confidence,
                    "serial_number": device.serial_number,
                    "firmware": device.firmware,
                    "location": group_name,
                },
            }
        )

    for device in observed_clients:
        label = device.hostname or device.vendor or device.mac_address
        nodes.append(
            {
                "id": f"observed-device-{device.id}",
                "device_id": device.id,
                "label": label,
                "group": "observed-clients",
                "shape": "dot",
                "kind": "observed",
                "title": f"{label}\nOnline observation; AP association unverified",
                "meta": {
                    "source": "network_observation",
                    "device_id": device.id,
                    "mac": device.mac_address,
                    "ip": device.ip_address,
                    "vendor": device.vendor,
                    "source_ap": device.source_ap,
                    "condition": "observation_only",
                },
            }
        )

    status_colors = {
        "reported": "#64748b",
        "observed": "#38bdf8",
        "associated": "#fbbf24",
        "verified": "#34d399",
    }
    edges: list[dict[str, Any]] = []
    for link in links:
        endpoints = sorted(link.endpoints, key=lambda endpoint: endpoint.side)
        if len(endpoints) != 2 or any(
            endpoint.device_id not in device_node_ids for endpoint in endpoints
        ):
            continue
        left, right = endpoints
        left_name = left.interface.name if left.interface else None
        right_name = right.interface.name if right.interface else None
        label = link.label or (
            f"{left_name or 'device'} ↔ {right_name or 'device'}"
            if left_name or right_name
            else ""
        )
        edges.append(
            {
                "id": f"link-{link.id}",
                "from": f"device-{left.device_id}",
                "to": f"device-{right.device_id}",
                "label": label,
                "dashes": link.verification_status != "verified" or link.medium == "logical",
                "color": {"color": status_colors[link.verification_status]},
                "meta": {
                    "link_id": link.id,
                    "label": link.label,
                    "link_type": link.link_type,
                    "medium": link.medium,
                    "verification_status": link.verification_status,
                    "confidence": link.confidence,
                    "source": link.source,
                    "verification_evidence": link.verification_evidence,
                    "notes": link.notes,
                    "evidence": link.evidence or {},
                    "endpoints": [
                        {
                            "side": left.side,
                            "device_id": left.device_id,
                            "device_label": (
                                left.device.label or left.device.hostname or left.device.mac_address
                            ),
                            "interface_id": left.interface_id,
                            "interface_name": left_name,
                        },
                        {
                            "side": right.side,
                            "device_id": right.device_id,
                            "device_label": (
                                right.device.label
                                or right.device.hostname
                                or right.device.mac_address
                            ),
                            "interface_id": right.interface_id,
                            "interface_name": right_name,
                        },
                    ],
                },
            }
        )

    return {
        "meta": {"source": "normalized_topology", "legacy_document_used": False},
        "zones": zones,
        "nodes": nodes,
        "edges": edges,
        "switch_ports": {},
        "stats": {
            "infrastructure_nodes": min(total_devices, len(devices)),
            "observed_devices": len(observed_clients),
            "links": len(edges),
            "truncated": total_devices > len(devices),
            "total_devices": total_devices,
        },
    }


@router.get("/links", response_model=schemas.NetworkLinkPageOut, dependencies=[READ])
async def list_normalized_links(
    verification_status: schemas.LinkStatus | None = None,
    device_id: int | None = Query(None, gt=0),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> schemas.NetworkLinkPageOut:
    stmt = select(models.NetworkLink).options(*_link_options())
    count_stmt = select(func.count(models.NetworkLink.id))
    if verification_status is not None:
        stmt = stmt.where(models.NetworkLink.verification_status == verification_status)
        count_stmt = count_stmt.where(models.NetworkLink.verification_status == verification_status)
    if device_id is not None:
        matching_links = select(models.LinkEndpoint.link_id).where(
            models.LinkEndpoint.device_id == device_id
        )
        stmt = stmt.where(models.NetworkLink.id.in_(matching_links))
        count_stmt = count_stmt.where(models.NetworkLink.id.in_(matching_links))
    total = int(await session.scalar(count_stmt) or 0)
    rows = await session.scalars(
        stmt.order_by(models.NetworkLink.created_at.desc(), models.NetworkLink.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return schemas.NetworkLinkPageOut(total=total, items=[_link_out(row) for row in rows])


@router.get("/links/{link_id}", response_model=schemas.NetworkLinkOut, dependencies=[READ])
async def get_normalized_link(
    link_id: int,
    session: AsyncSession = Depends(get_session),
) -> schemas.NetworkLinkOut:
    link = await _load_link(session, link_id)
    if link is None:
        raise HTTPException(404, "topology link not found")
    return _link_out(link)


@router.get("/topology/export", dependencies=[READ])
async def export_topology(
    format: str = Query("json", pattern="^(json|csv)$"),
    session: AsyncSession = Depends(get_session),
) -> Response:
    """Download a snapshot of normalized links and their append-only evidence."""
    links = list(
        await session.scalars(
            select(models.NetworkLink).options(*_link_options()).order_by(models.NetworkLink.id)
        )
    )
    observations = list(
        await session.scalars(
            select(models.TopologyObservation).order_by(
                models.TopologyObservation.observed_at,
                models.TopologyObservation.id,
            )
        )
    )
    exported_at = datetime.now(UTC).isoformat()
    if format == "json":
        payload = {
            "schema_version": 1,
            "exported_at": exported_at,
            "links": [
                _link_out(link).model_dump(mode="json")
                for link in links
            ],
            "observations": [
                schemas.TopologyObservationOut.model_validate(row).model_dump(mode="json")
                for row in observations
            ],
        }
        return JSONResponse(
            payload,
            headers={"Content-Disposition": 'attachment; filename="zyranet-topology.json"'},
        )

    columns = [
        "record_type", "id", "link_id", "device_id", "discovery_run_id",
        "side_a_device_id", "side_a_device_label", "side_a_interface_id", "side_a_interface_name",
        "side_b_device_id", "side_b_device_label", "side_b_interface_id", "side_b_interface_name",
        "label", "link_type", "medium", "verification_status", "confidence", "source",
        "verification_evidence", "evidence", "notes", "observed_at", "created_at", "updated_at",
        "created_by",
    ]
    rows: list[dict[str, Any]] = []
    for link in links:
        endpoints = sorted(link.endpoints, key=lambda endpoint: endpoint.side)
        endpoint_a = next((endpoint for endpoint in endpoints if endpoint.side == "A"), None)
        endpoint_b = next((endpoint for endpoint in endpoints if endpoint.side == "B"), None)
        rows.append(
            {
                "record_type": "link",
                "id": link.id,
                "link_id": link.id,
                "side_a_device_id": endpoint_a.device_id if endpoint_a else None,
                "side_a_device_label": (
                    (
                        endpoint_a.device.label
                        or endpoint_a.device.hostname
                        or endpoint_a.device.mac_address
                    )
                    if endpoint_a
                    else None
                ),
                "side_a_interface_id": endpoint_a.interface_id if endpoint_a else None,
                "side_a_interface_name": (
                    endpoint_a.interface.name
                    if endpoint_a and endpoint_a.interface
                    else None
                ),
                "side_b_device_id": endpoint_b.device_id if endpoint_b else None,
                "side_b_device_label": (
                    (
                        endpoint_b.device.label
                        or endpoint_b.device.hostname
                        or endpoint_b.device.mac_address
                    )
                    if endpoint_b
                    else None
                ),
                "side_b_interface_id": endpoint_b.interface_id if endpoint_b else None,
                "side_b_interface_name": (
                    endpoint_b.interface.name
                    if endpoint_b and endpoint_b.interface
                    else None
                ),
                "label": link.label,
                "link_type": link.link_type,
                "medium": link.medium,
                "verification_status": link.verification_status,
                "confidence": link.confidence,
                "source": link.source,
                "verification_evidence": link.verification_evidence,
                "evidence": json.dumps(link.evidence or {}, ensure_ascii=False),
                "notes": link.notes,
                "created_at": link.created_at.isoformat() if link.created_at else None,
                "updated_at": link.updated_at.isoformat() if link.updated_at else None,
                "created_by": link.created_by,
            }
        )
    for observation in observations:
        rows.append(
            {
                "record_type": "observation",
                "id": observation.id,
                "link_id": observation.link_id,
                "device_id": observation.device_id,
                "discovery_run_id": observation.discovery_run_id,
                "verification_status": observation.verification_status,
                "confidence": observation.confidence,
                "source": observation.source,
                "evidence": json.dumps(observation.evidence or {}, ensure_ascii=False),
                "notes": observation.notes,
                "observed_at": (
                    observation.observed_at.isoformat() if observation.observed_at else None
                ),
                "created_at": (
                    observation.created_at.isoformat() if observation.created_at else None
                ),
            }
        )
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=columns, lineterminator="\r\n")
    writer.writeheader()
    for row in rows:
        safe_row = {}
        for key, value in row.items():
            dangerous_prefixes = ("=", "+", "-", "@", "\t", "\r")
            if isinstance(value, str) and value.lstrip().startswith(dangerous_prefixes):
                value = "'" + value
            safe_row[key] = value
        writer.writerow(safe_row)
    return Response(
        output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="zyranet-topology.csv"'},
    )


@router.post("/links", status_code=201, response_model=schemas.NetworkLinkOut, dependencies=[WRITE])
async def create_normalized_link(
    body: schemas.NetworkLinkIn,
    request: Request,
    principal: Principal = Depends(require_role("operator")),
    session: AsyncSession = Depends(get_session),
) -> schemas.NetworkLinkOut:
    await _validate_endpoint_specs(session, body.endpoints)
    if not (
        (body.notes or "").strip()
        or (body.verification_evidence or "").strip()
        or body.evidence
    ):
        raise HTTPException(422, "link records require a source note or evidence")
    if body.verification_status == "verified" and (
        body.confidence is None or not (body.verification_evidence or "").strip()
    ):
        raise HTTPException(422, "verified links require confidence and verification evidence")

    link = models.NetworkLink(
        **body.model_dump(exclude={"endpoints"}),
        created_by=principal.username,
        endpoints=[models.LinkEndpoint(**endpoint.model_dump()) for endpoint in body.endpoints],
    )
    session.add(link)
    try:
        await session.flush()
        await _audit(
            session,
            request,
            principal,
            "topology.link_record.create",
            link.id,
            detail={
                "endpoints": [
                    {"side": endpoint.side, "device_id": endpoint.device_id,
                     "interface_id": endpoint.interface_id}
                    for endpoint in body.endpoints
                ],
                "verification_status": link.verification_status,
                "confidence": link.confidence,
                "verification_evidence": link.verification_evidence,
            },
        )
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(409, "could not create topology link") from exc
    saved = await _load_link(session, link.id)
    if saved is None:
        raise HTTPException(500, "created topology link could not be reloaded")
    return _link_out(saved)


@router.patch("/links/{link_id}", response_model=schemas.NetworkLinkOut, dependencies=[WRITE])
async def patch_normalized_link(
    link_id: int,
    body: schemas.NetworkLinkPatch,
    request: Request,
    principal: Principal = Depends(require_role("operator")),
    session: AsyncSession = Depends(get_session),
) -> schemas.NetworkLinkOut:
    link = await _load_link(session, link_id)
    if link is None:
        raise HTTPException(404, "topology link not found")
    before = _link_audit_state(link)
    fields = body.model_fields_set
    if not fields:
        raise HTTPException(422, "provide at least one topology link field to update")
    values = body.model_dump(exclude_unset=True)
    endpoints = values.pop("endpoints", None)
    required_fields = ("link_type", "medium", "verification_status", "source", "evidence")
    if any(name in fields and values.get(name) is None for name in required_fields):
        raise HTTPException(422, "link type, medium, status, source, and evidence cannot be null")
    if "endpoints" in fields and endpoints is None:
        raise HTTPException(422, "endpoints must contain one A endpoint and one B endpoint")
    if endpoints is not None and not {
        "verification_status", "confidence", "verification_evidence"
    }.issubset(fields):
        raise HTTPException(
            422,
            "endpoint changes require an explicit status, confidence, and "
            "verification evidence update",
        )
    verification_status = values.get("verification_status", link.verification_status)
    confidence = values.get("confidence", link.confidence)
    verification_evidence = values.get("verification_evidence", link.verification_evidence)
    if verification_status == "verified" and (
        confidence is None or not (verification_evidence or "").strip()
    ):
        raise HTTPException(422, "verified links require confidence and verification evidence")
    if endpoints is not None:
        await _validate_endpoint_specs(session, body.endpoints or [])
        link.endpoints.clear()
        await session.flush()
        link.endpoints = [models.LinkEndpoint(**endpoint) for endpoint in endpoints]
    for name, value in values.items():
        setattr(link, name, value)
    try:
        await session.flush()
        await _audit(
            session,
            request,
            principal,
            "topology.link_record.update",
            link_id,
            detail={
                "fields": sorted(fields),
                "before": before,
                "after": _link_audit_state(link),
            },
        )
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(409, "could not update topology link") from exc
    saved = await _load_link(session, link_id)
    if saved is None:
        raise HTTPException(500, "updated topology link could not be reloaded")
    return _link_out(saved)


@router.get(
    "/topology-observations",
    response_model=schemas.TopologyObservationPageOut,
    dependencies=[READ],
)
async def list_topology_observations(
    device_id: int | None = Query(None, gt=0),
    link_id: int | None = Query(None, gt=0),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> schemas.TopologyObservationPageOut:
    stmt = select(models.TopologyObservation)
    count_stmt = select(func.count(models.TopologyObservation.id))
    if device_id is not None:
        stmt = stmt.where(models.TopologyObservation.device_id == device_id)
        count_stmt = count_stmt.where(models.TopologyObservation.device_id == device_id)
    if link_id is not None:
        stmt = stmt.where(models.TopologyObservation.link_id == link_id)
        count_stmt = count_stmt.where(models.TopologyObservation.link_id == link_id)
    total = int(await session.scalar(count_stmt) or 0)
    rows = await session.scalars(
        stmt.order_by(
            models.TopologyObservation.observed_at.desc(),
            models.TopologyObservation.id.desc(),
        )
        .offset(offset)
        .limit(limit)
    )
    return schemas.TopologyObservationPageOut(
        total=total,
        items=[schemas.TopologyObservationOut.model_validate(row) for row in rows],
    )


@router.post(
    "/topology-observations",
    status_code=201,
    response_model=schemas.TopologyObservationOut,
    dependencies=[WRITE],
)
async def create_topology_observation(
    body: schemas.TopologyObservationIn,
    request: Request,
    principal: Principal = Depends(require_role("operator")),
    session: AsyncSession = Depends(get_session),
) -> schemas.TopologyObservationOut:
    if body.device_id is None and body.link_id is None:
        raise HTTPException(422, "an observation must reference a device or a link")
    if body.device_id is not None and await session.get(models.Device, body.device_id) is None:
        raise HTTPException(422, "observation device does not exist")
    if body.link_id is not None and await session.get(models.NetworkLink, body.link_id) is None:
        raise HTTPException(422, "observation link does not exist")
    if body.discovery_run_id is not None and await session.get(
        models.DiscoveryRun, body.discovery_run_id
    ) is None:
        raise HTTPException(422, "discovery run does not exist")
    if not body.evidence:
        raise HTTPException(422, "topology observations require evidence")
    if body.verification_status == "verified" and (
        body.confidence is None or not body.evidence
    ):
        raise HTTPException(422, "verified observations require confidence and evidence")

    observation = models.TopologyObservation(**body.model_dump(exclude_none=True))
    session.add(observation)
    try:
        await session.flush()
        await _audit(
            session,
            request,
            principal,
            "topology.observation.create",
            observation.id,
            detail={
                "device_id": observation.device_id,
                "link_id": observation.link_id,
                "source": observation.source,
                "verification_status": observation.verification_status,
            },
        )
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(409, "could not create topology observation") from exc
    await session.refresh(observation)
    return schemas.TopologyObservationOut.model_validate(observation)


@router.get(
    "/topology/document",
    response_model=TopologyDocumentOut,
    dependencies=[READ],
    deprecated=True,
)
async def get_document(session: AsyncSession = Depends(get_session)) -> TopologyDocumentOut:
    """Raw topology document for the editor."""
    doc = await topology_store.get_document(session)
    row = await session.get(models.TopologyDocument, _DOC_ID)
    return TopologyDocumentOut(document=doc, updated_at=row.updated_at if row else None)


@router.put(
    "/topology/document",
    response_model=TopologyDocumentOut,
    dependencies=[WRITE],
    deprecated=True,
)
async def put_document(
    body: TopologyDocumentIn,
    request: Request,
    principal: Principal = Depends(require_role("operator")),
    session: AsyncSession = Depends(get_session),
) -> TopologyDocumentOut:
    s = get_settings()
    doc = await topology_store.save_document(
        session, body.document, export_file=s.topology_auto_export
    )
    await _audit(
        session,
        request,
        principal,
        "topology.document.save",
        _DOC_ID,
        detail={"nodes": len(doc.get("nodes") or []), "links": len(doc.get("links") or [])},
    )
    row = await session.get(models.TopologyDocument, _DOC_ID)
    return TopologyDocumentOut(document=doc, updated_at=row.updated_at if row else None)


@router.patch("/topology/positions", dependencies=[WRITE], deprecated=True)
async def patch_positions(
    body: schemas.TopologyPositionsIn,
    request: Request,
    principal: Principal = Depends(require_role("operator")),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    s = get_settings()
    n = await topology_store.patch_positions(
        session, body.positions, export_file=s.topology_auto_export
    )
    await _audit(
        session, request, principal, "topology.position.update", _DOC_ID, detail={"updated": n}
    )
    return {"updated": n}


@router.post("/topology/nodes", status_code=201, dependencies=[WRITE], deprecated=True)
async def create_node(
    body: schemas.TopologyNodeIn,
    request: Request,
    principal: Principal = Depends(require_role("operator")),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    node = body.model_dump(exclude_none=True)
    existing = await topology_store.get_document(session)
    if any(n["id"] == node["id"] for n in existing.get("nodes") or []):
        raise HTTPException(409, "node id already exists")
    saved = await topology_store.upsert_node(session, node)
    await _audit(session, request, principal, "topology.node.create", node["id"])
    return saved


@router.put("/topology/nodes/{node_id}", dependencies=[WRITE], deprecated=True)
async def update_node(
    node_id: str,
    body: schemas.TopologyNodeIn,
    request: Request,
    principal: Principal = Depends(require_role("operator")),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    if body.id != node_id:
        raise HTTPException(400, "id mismatch")
    saved = await topology_store.upsert_node(session, body.model_dump(exclude_none=True))
    await _audit(session, request, principal, "topology.node.update", node_id)
    return saved


@router.delete("/topology/nodes/{node_id}", dependencies=[WRITE], deprecated=True)
async def remove_node(
    node_id: str,
    request: Request,
    principal: Principal = Depends(require_role("operator")),
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    if not await topology_store.delete_node(session, node_id):
        raise HTTPException(404, "node not found")
    await _audit(session, request, principal, "topology.node.delete", node_id)
    return {"deleted": node_id}


@router.post("/topology/links", status_code=201, dependencies=[WRITE], deprecated=True)
async def create_link(
    body: schemas.TopologyLinkIn,
    request: Request,
    principal: Principal = Depends(require_role("operator")),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    doc = await topology_store.get_document(session)
    node_ids = {n["id"] for n in doc.get("nodes") or []}
    if body.source not in node_ids or body.target not in node_ids:
        raise HTTPException(400, "source or target node missing")
    saved = await topology_store.upsert_link(session, body.model_dump(exclude_none=True))
    await _audit(
        session,
        request,
        principal,
        "topology.link.create",
        saved.get("id") or f"{body.source}->{body.target}",
        detail={"source": body.source, "target": body.target},
    )
    return saved


@router.put("/topology/links/{link_id}", dependencies=[WRITE], deprecated=True)
async def update_link(
    link_id: str,
    body: schemas.TopologyLinkIn,
    request: Request,
    principal: Principal = Depends(require_role("operator")),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    payload = body.model_dump(exclude_none=True)
    payload["id"] = link_id
    saved = await topology_store.upsert_link(session, payload)
    await _audit(
        session,
        request,
        principal,
        "topology.link.update",
        link_id,
        detail={"source": body.source, "target": body.target},
    )
    return saved


@router.delete("/topology/links/{link_id}", dependencies=[WRITE], deprecated=True)
async def remove_link(
    link_id: str,
    request: Request,
    principal: Principal = Depends(require_role("operator")),
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    if not await topology_store.delete_link(session, link_id):
        raise HTTPException(404, "link not found")
    await _audit(session, request, principal, "topology.link.delete", link_id)
    return {"deleted": link_id}


@router.post("/topology/discovery/run", dependencies=[WRITE])
async def run_snmp_discovery(
    request: Request,
    principal: Principal = Depends(require_role("operator")),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Run LLDP discovery against SNMP_TARGETS and return structured results."""
    s = get_settings()
    if not s.snmp_enabled:
        raise HTTPException(400, "SNMP discovery disabled (set SNMP_ENABLED=true)")
    if not s.snmp_targets.strip():
        raise HTTPException(400, "SNMP_TARGETS not configured")
    doc = await topology_store.get_document(session)
    result = await snmp_discover.run_discovery(s.snmp_targets, doc)
    await _audit(
        session,
        request,
        principal,
        "topology.discovery.run",
        _DOC_ID,
        detail={
            "summary": result.get("summary"),
            "suggestions": len(result.get("suggestions") or []),
        },
        outcome="success" if result.get("ok") else "failure",
    )
    return result


@router.post("/topology/discovery/apply", dependencies=[WRITE])
async def apply_discovery(
    body: schemas.TopologyApplyDiscoveryIn,
    request: Request,
    principal: Principal = Depends(require_role("operator")),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    specs = [lk.model_dump(exclude_none=True) for lk in body.links]
    added = await topology_store.apply_discovered_links(session, specs)
    await _audit(
        session,
        request,
        principal,
        "topology.discovery.apply",
        _DOC_ID,
        detail={"requested": len(specs), "added": len(added)},
    )
    return {"added": added, "count": len(added)}
