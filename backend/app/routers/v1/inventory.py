"""v1 inventory API: locations, device models + capabilities, devices.

Reads require at least the `viewer` role; writes require `operator`.
Every write appends an audit event.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ... import models, schemas
from ...config import get_settings
from ...db import get_session
from ...security import Principal, require_role
from ...services.audit import record_audit

router = APIRouter(tags=["inventory"])

READ = Depends(require_role("viewer"))
WRITE = Depends(require_role("operator"))


def _rid(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


async def _audit(
    session: AsyncSession,
    request: Request,
    principal: Principal,
    action: str,
    entity_type: str,
    entity_id: int,
    detail: dict[str, Any] | None = None,
) -> None:
    await record_audit(
        session,
        actor=principal.username,
        role=principal.role,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        detail=detail or {},
        request_id=_rid(request),
    )


def _conflict(msg: str) -> HTTPException:
    return HTTPException(409, msg)


def _missing(kind: str) -> HTTPException:
    return HTTPException(404, f"{kind} not found")


# ---------------------------------------------------------------------------
# Locations
# ---------------------------------------------------------------------------


@router.get("/locations", response_model=list[schemas.LocationOut])
async def list_locations(
    kind: str | None = None,
    q: str | None = Query(None, description="filter by name/code"),
    session: AsyncSession = Depends(get_session),
    _: Principal = READ,
):
    stmt = select(models.Location).order_by(models.Location.kind, models.Location.name)
    if kind:
        stmt = stmt.where(models.Location.kind == kind)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(models.Location.name.ilike(like), models.Location.code.ilike(like))
        )
    return list(await session.scalars(stmt))


@router.post("/locations", status_code=201, response_model=schemas.LocationOut)
async def create_location(
    payload: schemas.LocationIn,
    request: Request,
    session: AsyncSession = Depends(get_session),
    principal: Principal = WRITE,
):
    if payload.parent_id is not None and await session.get(
        models.Location, payload.parent_id
    ) is None:
        raise HTTPException(422, "parent location does not exist")
    loc = models.Location(**payload.model_dump())
    session.add(loc)
    try:
        await session.flush()
        await _audit(session, request, principal, "location.create", "location", loc.id,
                     {"name": loc.name, "kind": loc.kind})
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise _conflict("could not create location") from exc
    return loc


@router.get("/locations/{location_id}", response_model=schemas.LocationOut)
async def get_location(
    location_id: int,
    session: AsyncSession = Depends(get_session),
    _: Principal = READ,
):
    loc = await session.get(models.Location, location_id)
    if loc is None:
        raise _missing("location")
    return loc


@router.patch("/locations/{location_id}", response_model=schemas.LocationOut)
async def patch_location(
    location_id: int,
    payload: schemas.LocationPatch,
    request: Request,
    session: AsyncSession = Depends(get_session),
    principal: Principal = WRITE,
):
    loc = await session.get(models.Location, location_id)
    if loc is None:
        raise _missing("location")
    fields = payload.model_fields_set
    if "parent_id" in fields:
        if payload.parent_id == location_id:
            raise HTTPException(422, "a location cannot be its own parent")
        if payload.parent_id is not None and await session.get(
            models.Location, payload.parent_id
        ) is None:
            raise HTTPException(422, "parent location does not exist")
    for name in fields:
        setattr(loc, name, getattr(payload, name))
    await _audit(session, request, principal, "location.update", "location", loc.id,
                 {"fields": sorted(fields)})
    await session.commit()
    return loc


@router.delete("/locations/{location_id}", status_code=204)
async def delete_location(
    location_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
    principal: Principal = WRITE,
):
    loc = await session.get(models.Location, location_id)
    if loc is None:
        raise _missing("location")
    children = await session.scalar(
        select(func.count()).select_from(models.Location).where(
            models.Location.parent_id == location_id
        )
    )
    if children:
        raise _conflict("location still has child locations")
    devices = await session.scalar(
        select(func.count()).select_from(models.Device).where(
            models.Device.location_id == location_id
        )
    )
    if devices:
        raise _conflict("location still has assigned devices")
    await _audit(session, request, principal, "location.delete", "location", loc.id,
                 {"name": loc.name})
    await session.delete(loc)
    await session.commit()


# ---------------------------------------------------------------------------
# Device models + capabilities
# ---------------------------------------------------------------------------


def _device_model_options():
    return (selectinload(models.DeviceModel.capabilities),)


@router.get("/device-models", response_model=schemas.DeviceModelPageOut)
async def list_device_models(
    vendor: str | None = None,
    q: str | None = Query(None, description="filter by vendor/model/family"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
    _: Principal = READ,
):
    stmt = select(models.DeviceModel).options(*_device_model_options()).order_by(
        models.DeviceModel.vendor, models.DeviceModel.model
    )
    count_stmt = select(func.count()).select_from(models.DeviceModel)
    if vendor:
        stmt = stmt.where(models.DeviceModel.vendor.ilike(vendor))
        count_stmt = count_stmt.where(models.DeviceModel.vendor.ilike(vendor))
    if q:
        like = f"%{q}%"
        cond = or_(
            models.DeviceModel.vendor.ilike(like),
            models.DeviceModel.model.ilike(like),
            models.DeviceModel.family.ilike(like),
        )
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)
    total = int(await session.scalar(count_stmt) or 0)
    rows = await session.scalars(stmt.offset(offset).limit(limit))
    return schemas.DeviceModelPageOut(
        total=total,
        items=[schemas.DeviceModelOut.model_validate(r) for r in rows],
    )


@router.post("/device-models", status_code=201, response_model=schemas.DeviceModelOut)
async def create_device_model(
    payload: schemas.DeviceModelIn,
    request: Request,
    session: AsyncSession = Depends(get_session),
    principal: Principal = WRITE,
):
    data = payload.model_dump(exclude={"capabilities"})
    model = models.DeviceModel(**data)
    for cap in payload.capabilities:
        model.capabilities.append(models.DeviceCapability(**cap.model_dump()))
    session.add(model)
    try:
        await session.flush()
        await _audit(session, request, principal, "device_model.create", "device_model",
                     model.id, {"vendor": model.vendor, "model": model.model})
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise _conflict("a device model with this vendor/model/revision already exists") from exc
    await session.refresh(model, ["capabilities"])
    return model


@router.get("/device-models/{model_id}", response_model=schemas.DeviceModelOut)
async def get_device_model(
    model_id: int,
    session: AsyncSession = Depends(get_session),
    _: Principal = READ,
):
    model = await session.scalar(
        select(models.DeviceModel)
        .where(models.DeviceModel.id == model_id)
        .options(*_device_model_options())
    )
    if model is None:
        raise _missing("device model")
    return model


@router.patch("/device-models/{model_id}", response_model=schemas.DeviceModelOut)
async def patch_device_model(
    model_id: int,
    payload: schemas.DeviceModelPatch,
    request: Request,
    session: AsyncSession = Depends(get_session),
    principal: Principal = WRITE,
):
    model = await session.scalar(
        select(models.DeviceModel)
        .where(models.DeviceModel.id == model_id)
        .options(*_device_model_options())
    )
    if model is None:
        raise _missing("device model")
    fields = payload.model_fields_set
    for name in fields:
        setattr(model, name, getattr(payload, name))
    try:
        await _audit(session, request, principal, "device_model.update", "device_model",
                     model.id, {"fields": sorted(fields)})
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise _conflict("a device model with this vendor/model/revision already exists") from exc
    return model


@router.delete("/device-models/{model_id}", status_code=204)
async def delete_device_model(
    model_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
    principal: Principal = WRITE,
):
    model = await session.get(models.DeviceModel, model_id)
    if model is None:
        raise _missing("device model")
    devices = await session.scalar(
        select(func.count()).select_from(models.Device).where(
            models.Device.model_id == model_id
        )
    )
    if devices:
        raise _conflict("device model is still assigned to devices")
    await _audit(session, request, principal, "device_model.delete", "device_model",
                 model_id, {"vendor": model.vendor, "model": model.model})
    await session.delete(model)
    await session.commit()


# ---------------------------------------------------------------------------
# Devices
# ---------------------------------------------------------------------------


def _device_options():
    return (
        selectinload(models.Device.model).selectinload(models.DeviceModel.capabilities),
        selectinload(models.Device.location),
    )


@router.get("/devices", response_model=schemas.DevicePageOut)
async def list_devices(
    q: str | None = Query(None, description="filter by MAC/IP/hostname/vendor/label"),
    location_id: int | None = None,
    model_id: int | None = None,
    online: bool | None = None,
    observation_status: str | None = Query(None, pattern="^(observed|stale|unknown)$"),
    condition: str | None = None,
    type: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
    _: Principal = READ,
):
    stmt = select(models.Device).options(*_device_options()).order_by(
        models.Device.last_seen.desc()
    )
    count_stmt = select(func.count()).select_from(models.Device)
    if q:
        like = f"%{q}%"
        cond = or_(
            models.Device.mac_address.ilike(like),
            models.Device.ip_address.ilike(like),
            models.Device.hostname.ilike(like),
            models.Device.vendor.ilike(like),
            models.Device.label.ilike(like),
        )
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)
    for column, value in (
        (models.Device.location_id, location_id),
        (models.Device.model_id, model_id),
        (models.Device.online, online),
        (models.Device.condition, condition),
        (models.Device.type, type),
    ):
        if value is not None:
            stmt = stmt.where(column == value)
            count_stmt = count_stmt.where(column == value)
    if observation_status is not None:
        cutoff = datetime.now(UTC) - timedelta(
            seconds=max(60, get_settings().device_stale_after_seconds)
        )
        if observation_status == "observed":
            status_filter = models.Device.online.is_(True) & (models.Device.last_seen >= cutoff)
        elif observation_status == "stale":
            status_filter = models.Device.online.is_(True) & (models.Device.last_seen < cutoff)
        else:
            status_filter = models.Device.online.is_(False)
        stmt = stmt.where(status_filter)
        count_stmt = count_stmt.where(status_filter)
    total = int(await session.scalar(count_stmt) or 0)
    rows = await session.scalars(stmt.offset(offset).limit(limit))
    return schemas.DevicePageOut(
        total=total,
        items=[schemas.DeviceOut.model_validate(d) for d in rows],
    )


@router.post("/devices", status_code=201, response_model=schemas.DeviceOut)
async def create_device(
    payload: schemas.DeviceIn,
    request: Request,
    session: AsyncSession = Depends(get_session),
    principal: Principal = WRITE,
):
    if payload.model_id is not None and await session.get(
        models.DeviceModel, payload.model_id
    ) is None:
        raise HTTPException(422, "device model does not exist")
    if payload.location_id is not None and await session.get(
        models.Location, payload.location_id
    ) is None:
        raise HTTPException(422, "location does not exist")

    data = payload.model_dump(exclude={"interfaces", "mac_address"})
    device = models.Device(mac_address=payload.mac_address.lower(), **data)
    for iface in payload.interfaces:
        device.interfaces.append(models.DeviceInterface(**iface.model_dump()))
    session.add(device)
    try:
        await session.flush()
        await _audit(session, request, principal, "device.create", "device", device.id,
                     {"mac": device.mac_address, "label": device.label})
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise _conflict("a device with this MAC address already exists") from exc
    return await _load_device(session, device.id)


@router.get("/devices/{device_id}", response_model=schemas.DeviceOut)
async def get_device(
    device_id: int,
    session: AsyncSession = Depends(get_session),
    _: Principal = READ,
):
    device = await _load_device(session, device_id)
    if device is None:
        raise _missing("device")
    return device


@router.patch("/devices/{device_id}", response_model=schemas.DeviceOut)
async def patch_device(
    device_id: int,
    payload: schemas.DevicePatch,
    request: Request,
    session: AsyncSession = Depends(get_session),
    principal: Principal = WRITE,
):
    device = await session.get(models.Device, device_id)
    if device is None:
        raise _missing("device")
    fields = payload.model_fields_set
    if "model_id" in fields and payload.model_id is not None:
        if await session.get(models.DeviceModel, payload.model_id) is None:
            raise HTTPException(422, "device model does not exist")
    if "location_id" in fields and payload.location_id is not None:
        if await session.get(models.Location, payload.location_id) is None:
            raise HTTPException(422, "location does not exist")
    for name in fields:
        setattr(device, name, getattr(payload, name))
    await _audit(session, request, principal, "device.update", "device", device.id,
                 {"fields": sorted(fields)})
    await session.commit()
    return await _load_device(session, device.id)


@router.delete("/devices/{device_id}", status_code=204)
async def delete_device(
    device_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
    principal: Principal = WRITE,
):
    device = await session.get(models.Device, device_id)
    if device is None:
        raise _missing("device")
    linked_endpoints = int(
        await session.scalar(
            select(func.count()).select_from(models.LinkEndpoint).where(
                models.LinkEndpoint.device_id == device_id
            )
        ) or 0
    )
    topology_evidence = int(
        await session.scalar(
            select(func.count()).select_from(models.TopologyObservation).where(
                models.TopologyObservation.device_id == device_id
            )
        ) or 0
    )
    if linked_endpoints or topology_evidence:
        raise _conflict(
            "device has topology links or evidence; retire it instead of deleting its history"
        )
    mac = device.mac_address
    await _audit(session, request, principal, "device.delete", "device", device.id,
                 {"mac": mac})
    # Sightings/interfaces/addresses are removed by ORM cascade; audit stays.
    await session.execute(
        delete(models.DeviceSighting).where(models.DeviceSighting.device_id == device_id)
    )
    await session.delete(device)
    await session.commit()


async def _load_device(session: AsyncSession, device_id: int) -> models.Device | None:
    return await session.scalar(
        select(models.Device)
        .where(models.Device.id == device_id)
        .options(*_device_options())
    )


# ---------------------------------------------------------------------------
# Device interfaces
# ---------------------------------------------------------------------------


@router.get(
    "/devices/{device_id}/interfaces",
    response_model=list[schemas.DeviceInterfaceOut],
)
async def list_interfaces(
    device_id: int,
    session: AsyncSession = Depends(get_session),
    _: Principal = READ,
):
    if await session.get(models.Device, device_id) is None:
        raise _missing("device")
    rows = await session.scalars(
        select(models.DeviceInterface)
        .where(models.DeviceInterface.device_id == device_id)
        .order_by(models.DeviceInterface.name)
    )
    return list(rows)


@router.post(
    "/devices/{device_id}/interfaces",
    status_code=201,
    response_model=schemas.DeviceInterfaceOut,
)
async def create_interface(
    device_id: int,
    payload: schemas.DeviceInterfaceIn,
    request: Request,
    session: AsyncSession = Depends(get_session),
    principal: Principal = WRITE,
):
    if await session.get(models.Device, device_id) is None:
        raise _missing("device")
    iface = models.DeviceInterface(device_id=device_id, **payload.model_dump())
    session.add(iface)
    try:
        await session.flush()
        await _audit(session, request, principal, "device.interface.create", "device",
                     device_id, {"name": iface.name})
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise _conflict("this interface name already exists on the device") from exc
    return iface


@router.patch(
    "/devices/{device_id}/interfaces/{iface_id}",
    response_model=schemas.DeviceInterfaceOut,
)
async def patch_interface(
    device_id: int,
    iface_id: int,
    payload: schemas.DeviceInterfaceIn,
    request: Request,
    session: AsyncSession = Depends(get_session),
    principal: Principal = WRITE,
):
    iface = await session.scalar(
        select(models.DeviceInterface).where(
            models.DeviceInterface.id == iface_id,
            models.DeviceInterface.device_id == device_id,
        )
    )
    if iface is None:
        raise _missing("interface")
    for name, value in payload.model_dump().items():
        setattr(iface, name, value)
    await _audit(session, request, principal, "device.interface.update", "device",
                 device_id, {"interface": iface.name})
    await session.commit()
    return iface


@router.delete("/devices/{device_id}/interfaces/{iface_id}", status_code=204)
async def delete_interface(
    device_id: int,
    iface_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
    principal: Principal = WRITE,
):
    iface = await session.scalar(
        select(models.DeviceInterface).where(
            models.DeviceInterface.id == iface_id,
            models.DeviceInterface.device_id == device_id,
        )
    )
    if iface is None:
        raise _missing("interface")
    linked_endpoints = int(
        await session.scalar(
            select(func.count()).select_from(models.LinkEndpoint).where(
                models.LinkEndpoint.interface_id == iface_id
            )
        ) or 0
    )
    if linked_endpoints:
        raise _conflict(
            "interface is referenced by topology links; update those link endpoints first"
        )
    await _audit(session, request, principal, "device.interface.delete", "device",
                 device_id, {"interface": iface.name})
    await session.delete(iface)
    await session.commit()


# ---------------------------------------------------------------------------
# Device addresses (history)
# ---------------------------------------------------------------------------


@router.get(
    "/devices/{device_id}/addresses",
    response_model=list[schemas.DeviceAddressOut],
)
async def list_addresses(
    device_id: int,
    session: AsyncSession = Depends(get_session),
    _: Principal = READ,
):
    if await session.get(models.Device, device_id) is None:
        raise _missing("device")
    rows = await session.scalars(
        select(models.DeviceAddress)
        .where(models.DeviceAddress.device_id == device_id)
        .order_by(models.DeviceAddress.current.desc(), models.DeviceAddress.last_seen.desc())
    )
    return list(rows)


@router.post(
    "/devices/{device_id}/addresses",
    status_code=201,
    response_model=schemas.DeviceAddressOut,
)
async def create_address(
    device_id: int,
    payload: schemas.DeviceAddressIn,
    request: Request,
    session: AsyncSession = Depends(get_session),
    principal: Principal = WRITE,
):
    if await session.get(models.Device, device_id) is None:
        raise _missing("device")
    existing = await session.scalar(
        select(models.DeviceAddress).where(
            models.DeviceAddress.device_id == device_id,
            models.DeviceAddress.address == payload.address,
            models.DeviceAddress.current.is_(True),
        )
    )
    if existing:
        # Known address seen again: refresh timestamps instead of duplicating.
        existing.last_seen = datetime.now(UTC)
        existing.source = payload.source
        if payload.prefix_length is not None:
            existing.prefix_length = payload.prefix_length
        await _audit(session, request, principal, "device.address.observe", "device",
                     device_id, {"address": payload.address})
        await session.commit()
        return existing

    addr = models.DeviceAddress(device_id=device_id, **payload.model_dump())
    session.add(addr)
    await session.flush()
    await _audit(session, request, principal, "device.address.create", "device",
                 device_id, {"address": payload.address, "source": payload.source})
    await session.commit()
    return addr
