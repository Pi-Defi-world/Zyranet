"""Network topology map API (admin)."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..db import get_session
from ..schemas import TopologyApplyDiscoveryIn, TopologyLinkIn, TopologyNodeIn, TopologyPositionsIn
from ..security import require_admin
from ..services import snmp_discover, topology
from ..services import topology_store

router = APIRouter(prefix="/network", tags=["network"], dependencies=[Depends(require_admin)])


class TopologyDocumentIn(BaseModel):
    document: dict[str, Any]


@router.get("/topology")
async def get_topology(
    include_clients: bool = Query(True, description="Attach live scanned devices to APs"),
    client_limit: int = Query(80, ge=0, le=200),
    session: AsyncSession = Depends(get_session),
):
    """Full graph for the admin network map (DB layout + live overlay)."""
    return await topology.build_topology(
        session, include_clients=include_clients, client_limit=client_limit
    )


@router.get("/document")
async def get_document(session: AsyncSession = Depends(get_session)):
    """Raw topology document for the editor."""
    from .. import models

    doc = await topology_store.get_document(session)
    row = await session.get(models.TopologyDocument, 1)
    return {"document": doc, "updated_at": row.updated_at if row else None}


@router.put("/document")
async def put_document(
    body: TopologyDocumentIn,
    session: AsyncSession = Depends(get_session),
):
    s = get_settings()
    doc = await topology_store.save_document(
        session, body.document, export_file=s.topology_auto_export
    )
    return {"document": doc}


@router.patch("/positions")
async def patch_positions(
    body: TopologyPositionsIn,
    session: AsyncSession = Depends(get_session),
):
    s = get_settings()
    n = await topology_store.patch_positions(
        session, body.positions, export_file=s.topology_auto_export
    )
    return {"updated": n}


@router.post("/nodes")
async def create_node(body: TopologyNodeIn, session: AsyncSession = Depends(get_session)):
    node = body.model_dump(exclude_none=True)
    existing = await topology_store.get_document(session)
    if any(n["id"] == node["id"] for n in existing.get("nodes") or []):
        raise HTTPException(409, "node id already exists")
    saved = await topology_store.upsert_node(session, node)
    return saved


@router.put("/nodes/{node_id}")
async def update_node(
    node_id: str, body: TopologyNodeIn, session: AsyncSession = Depends(get_session)
):
    if body.id != node_id:
        raise HTTPException(400, "id mismatch")
    saved = await topology_store.upsert_node(session, body.model_dump(exclude_none=True))
    return saved


@router.delete("/nodes/{node_id}")
async def remove_node(node_id: str, session: AsyncSession = Depends(get_session)):
    if not await topology_store.delete_node(session, node_id):
        raise HTTPException(404, "node not found")
    return {"deleted": node_id}


@router.post("/links")
async def create_link(body: TopologyLinkIn, session: AsyncSession = Depends(get_session)):
    doc = await topology_store.get_document(session)
    node_ids = {n["id"] for n in doc.get("nodes") or []}
    if body.source not in node_ids or body.target not in node_ids:
        raise HTTPException(400, "source or target node missing")
    saved = await topology_store.upsert_link(session, body.model_dump(exclude_none=True))
    return saved


@router.put("/links/{link_id}")
async def update_link(
    link_id: str, body: TopologyLinkIn, session: AsyncSession = Depends(get_session)
):
    payload = body.model_dump(exclude_none=True)
    payload["id"] = link_id
    saved = await topology_store.upsert_link(session, payload)
    return saved


@router.delete("/links/{link_id}")
async def remove_link(link_id: str, session: AsyncSession = Depends(get_session)):
    if not await topology_store.delete_link(session, link_id):
        raise HTTPException(404, "link not found")
    return {"deleted": link_id}


@router.post("/discover/snmp")
async def discover_snmp(session: AsyncSession = Depends(get_session)):
    s = get_settings()
    if not s.snmp_enabled:
        raise HTTPException(400, "SNMP discovery disabled (set SNMP_ENABLED=true)")
    raw = s.snmp_targets.strip()
    if not raw:
        raise HTTPException(400, "SNMP_TARGETS not configured")
    doc = await topology_store.get_document(session)
    return await snmp_discover.run_discovery(raw, doc, default_community=s.snmp_community)


@router.post("/discover/apply")
async def apply_discovery(
    body: TopologyApplyDiscoveryIn,
    session: AsyncSession = Depends(get_session),
):
    specs = [lk.model_dump(exclude_none=True) for lk in body.links]
    added = await topology_store.apply_discovered_links(session, specs)
    return {"added": added, "count": len(added)}


@router.post("/export-file")
async def export_topology_file(session: AsyncSession = Depends(get_session)):
    doc = await topology_store.get_document(session)
    path = topology_store.export_document_to_file(doc)
    return {"path": str(path)}
