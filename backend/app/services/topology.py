"""Build a recorded infrastructure graph with optional unattached observations."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models
from . import topology_store

_KIND_SHAPES = {
    "wan": "dot",
    "router": "box",
    "switch": "box",
    "server": "database",
    "radio": "triangle",
    "ap": "star",
    "service": "ellipse",
    "observed": "dot",
}


def _port_label(link: dict[str, Any]) -> str:
    parts: list[str] = []
    if link.get("source_port"):
        sp = link["source_port"]
        parts.append(f"P{sp}" if str(sp).isdigit() else sp)
    if link.get("target_port"):
        tgt = link["target_port"]
        parts.append(f"→ P{tgt}" if str(tgt).isdigit() else f"→ {tgt}")
    if link.get("label") and not parts:
        return link["label"]
    return " · ".join(parts) if parts else link.get("label") or ""


def _vis_node(
    node: dict[str, Any], *, dynamic: bool = False, online: bool | None = None
) -> dict[str, Any]:
    kind = node.get("kind", "unknown")
    zone = node.get("zone", "core")
    title_parts = [node.get("label", node["id"])]
    if node.get("subtitle"):
        title_parts.append(node["subtitle"])
    if node.get("mgmt_ip"):
        title_parts.append(f"IP: {node['mgmt_ip']}")
    if node.get("ssid"):
        title_parts.append(f"SSID: {node['ssid']}")
    if node.get("mac"):
        title_parts.append(f"MAC: {node['mac']}")
    if node.get("ip"):
        title_parts.append(f"IP: {node['ip']}")
    if node.get("vendor"):
        title_parts.append(node["vendor"])
    if kind == "switch" and node.get("ports"):
        title_parts.append(f"{node['ports']} ports (unmanaged)")

    fixed = node.get("fixed") or {}
    out: dict[str, Any] = {
        "id": node["id"],
        "label": node.get("label", node["id"]),
        "group": zone,
        "shape": _KIND_SHAPES.get(kind, "dot"),
        "kind": kind,
        "title": "\n".join(title_parts),
        "meta": {k: v for k, v in node.items() if k not in ("fixed",)},
    }
    if fixed.get("x") is not None and fixed.get("y") is not None:
        out["x"] = fixed["x"]
        out["y"] = fixed["y"]
        out["fixed"] = {"x": True, "y": True}
    if dynamic:
        out["fixed"] = False
    if online is True:
        out["borderWidth"] = 3
        out["color"] = {"border": "#22c55e", "background": out.get("color", {}).get("background")}
    elif online is False:
        out["borderWidth"] = 1
    return out


async def build_topology(
    session: AsyncSession, *, include_observations: bool = True, client_limit: int = 80
) -> dict[str, Any]:
    """Return graph nodes and edges with their stored evidence metadata."""
    static = deepcopy(await topology_store.get_document(session))
    nodes_raw = deepcopy(static.get("nodes") or [])
    links = static.get("links") or []
    node_ids = {n["id"] for n in nodes_raw}
    devices: list[models.Device] = []
    if include_observations:
        devices = list(
            await session.scalars(
                select(models.Device)
                .where(models.Device.online.is_(True))
                .order_by(models.Device.last_seen.desc())
                .limit(client_limit)
            )
        )

    vis_nodes = [_vis_node(node) for node in nodes_raw]

    vis_edges = []
    for link in links:
        if link["source"] not in node_ids or link["target"] not in node_ids:
            continue
        medium = link.get("medium", "ethernet")
        dashes = medium == "wireless"
        color = {"color": "#64748b"}
        if medium == "wireless":
            color = {"color": "#38bdf8"}
        elif medium == "logical":
            color = {"color": "#a78bfa"}
            dashes = True
        if link.get("discovered"):
            color = {"color": "#06b6d4"}
        vis_edges.append(
            {
                "id": link["id"],
                "from": link["source"],
                "to": link["target"],
                "label": _port_label(link),
                "font": {"size": 10, "align": "middle"},
                "arrows": "to",
                "dashes": dashes or bool(link.get("discovered")),
                "color": color,
                "title": link.get("label") or _port_label(link),
                "meta": link,
            }
        )

    # Device observations remain unattached until an authoritative association
    # source can support a real AP relationship.
    offset_idx = 0
    for d in devices:
        if d.type in ("router", "ap"):
            continue
        observed_id = f"device-{d.mac_address.replace(':', '')}"
        offset_idx += 1
        observed_node = {
            "id": observed_id,
            "device_id": d.id,
            "label": (d.hostname or d.vendor or "Observed device")[:18],
            "kind": "observed",
            "zone": "unknown",
            "subtitle": "Observation; association unverified",
            "mac": d.mac_address,
            "ip": d.ip_address,
            "vendor": d.vendor,
            "source_ap": d.source_ap,
            "fixed": {
                "x": 1000 + 90 * (offset_idx % 3),
                "y": 180 + (offset_idx // 3) * 60,
            },
        }
        vis_nodes.append(_vis_node(observed_node, dynamic=True, online=d.online))

    switch_port_map: dict[str, list[dict[str, Any]]] = {}
    for link in links:
        ends = ((link.get("source"), "source_port"), (link.get("target"), "target_port"))
        for end, port_key in ends:
            if not end or not link.get(port_key):
                continue
            node = next(
                (n for n in nodes_raw if n["id"] == end and n.get("kind") == "switch"),
                None,
            )
            if not node:
                continue
            switch_port_map.setdefault(end, []).append(
                {
                    "port": link[port_key],
                    "peer": link["target"] if end == link.get("source") else link["source"],
                    "medium": link.get("medium"),
                    "label": link.get("label"),
                    "discovered": bool(link.get("discovered")),
                }
            )

    return {
        "meta": static.get("meta"),
        "zones": static.get("zones"),
        "nodes": vis_nodes,
        "edges": vis_edges,
        "switch_ports": switch_port_map,
        "stats": {
            "infrastructure_nodes": len(nodes_raw),
            "observed_devices": len([d for d in devices if d.type not in ("router", "ap")]),
            "links": len(vis_edges),
        },
    }
