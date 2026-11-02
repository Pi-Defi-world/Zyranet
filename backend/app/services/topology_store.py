"""Persist network topology document (JSON) in PostgreSQL / SQLite."""
from __future__ import annotations

import json
import logging
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models

log = logging.getLogger("zyranet.topology_store")

_DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "cet_topology.json"
_DOC_ID = 1


def _now() -> datetime:
    return datetime.now(timezone.utc)


def load_seed_from_file() -> dict[str, Any]:
    with _DEFAULT_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def export_document_to_file(document: dict[str, Any], path: Path | None = None) -> Path:
    dest = path or _DEFAULT_PATH
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(document, f, indent=2)
        f.write("\n")
    tmp.replace(dest)
    return dest


async def get_document(session: AsyncSession, *, seed_if_missing: bool = True) -> dict[str, Any]:
    row = await session.get(models.TopologyDocument, _DOC_ID)
    if row is None:
        if not seed_if_missing:
            return {"meta": {"name": "empty"}, "zones": [], "nodes": [], "links": []}
        doc = load_seed_from_file()
        row = models.TopologyDocument(id=_DOC_ID, data=json.dumps(doc), updated_at=_now())
        session.add(row)
        await session.commit()
        await session.refresh(row)
        return deepcopy(doc)
    return json.loads(row.data)


async def save_document(
    session: AsyncSession,
    document: dict[str, Any],
    *,
    export_file: bool = True,
) -> dict[str, Any]:
    row = await session.get(models.TopologyDocument, _DOC_ID)
    payload = json.dumps(document)
    if row is None:
        row = models.TopologyDocument(id=_DOC_ID, data=payload, updated_at=_now())
        session.add(row)
    else:
        row.data = payload
        row.updated_at = _now()
    await session.commit()
    if export_file:
        try:
            export_document_to_file(document)
        except OSError as exc:
            log.warning("topology export to file failed: %s", exc)
    return document


async def patch_positions(
    session: AsyncSession,
    positions: dict[str, dict[str, float]],
    *,
    export_file: bool = True,
) -> int:
    doc = await get_document(session)
    updated = 0
    by_id = {n["id"]: n for n in doc.get("nodes") or []}
    for nid, pos in positions.items():
        node = by_id.get(nid)
        if not node:
            continue
        node["fixed"] = {"x": float(pos["x"]), "y": float(pos["y"])}
        updated += 1
    if updated:
        await save_document(session, doc, export_file=export_file)
    return updated


def _new_link_id() -> str:
    return f"lk-{int(_now().timestamp() * 1000)}"


async def upsert_node(session: AsyncSession, node: dict[str, Any]) -> dict[str, Any]:
    doc = await get_document(session)
    nodes = doc.setdefault("nodes", [])
    idx = next((i for i, n in enumerate(nodes) if n["id"] == node["id"]), None)
    if idx is None:
        nodes.append(node)
    else:
        nodes[idx] = {**nodes[idx], **node}
    await save_document(session, doc)
    return node


async def delete_node(session: AsyncSession, node_id: str) -> bool:
    doc = await get_document(session)
    nodes = doc.get("nodes") or []
    before = len(nodes)
    doc["nodes"] = [n for n in nodes if n["id"] != node_id]
    if len(doc["nodes"]) == before:
        return False
    doc["links"] = [
        lk
        for lk in doc.get("links") or []
        if lk.get("source") != node_id and lk.get("target") != node_id
    ]
    await save_document(session, doc)
    return True


async def upsert_link(session: AsyncSession, link: dict[str, Any]) -> dict[str, Any]:
    doc = await get_document(session)
    links = doc.setdefault("links", [])
    if not link.get("id"):
        link["id"] = _new_link_id()
    idx = next((i for i, lk in enumerate(links) if lk["id"] == link["id"]), None)
    if idx is None:
        links.append(link)
    else:
        links[idx] = {**links[idx], **link}
    await save_document(session, doc)
    return link


async def delete_link(session: AsyncSession, link_id: str) -> bool:
    doc = await get_document(session)
    links = doc.get("links") or []
    doc["links"] = [lk for lk in links if lk.get("id") != link_id]
    if len(doc["links"]) == len(links):
        return False
    await save_document(session, doc)
    return True


async def apply_discovered_links(
    session: AsyncSession, link_specs: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Merge SNMP/LLDP suggested links into the document (skip duplicates)."""
    doc = await get_document(session)
    links = doc.setdefault("links", [])
    existing = {(lk.get("source"), lk.get("target"), lk.get("source_port"), lk.get("target_port")) for lk in links}
    added: list[dict[str, Any]] = []
    for spec in link_specs:
        key = (spec.get("source"), spec.get("target"), spec.get("source_port"), spec.get("target_port"))
        if key in existing:
            continue
        spec = {**spec, "id": spec.get("id") or _new_link_id(), "discovered": True}
        links.append(spec)
        existing.add(key)
        added.append(spec)
    if added:
        await save_document(session, doc)
    return added
