"""Build a Packet Tracer–style topology graph: static infrastructure + live clients."""
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
    "client": "dot",
    "session": "dot",
}


def _port_label(link: dict[str, Any]) -> str:
    parts: list[str] = []
    if link.get("source_port"):
        parts.append(f"P{link['source_port']}" if str(link["source_port"]).isdigit() else link["source_port"])
    if link.get("target_port"):
        tgt = link["target_port"]
        parts.append(f"→ P{tgt}" if str(tgt).isdigit() else f"→ {tgt}")
    if link.get("label") and not parts:
        return link["label"]
    return " · ".join(parts) if parts else link.get("label") or ""


def _resolve_ap_id(static: dict[str, Any], source_ap: str | None) -> str:
    cfg = static.get("client_attachment") or {}
    default = cfg.get("default_ap") or "ap-bldg-b-1"
    if not source_ap:
        return default
    key = source_ap.strip().lower()
    aliases = cfg.get("ap_aliases") or {}
    if key in aliases:
        return aliases[key]
    for node in static.get("nodes") or []:
        if node.get("kind") == "ap" and key in (node.get("label") or "").lower():
            return node["id"]
    return default


def _vis_node(node: dict[str, Any], *, dynamic: bool = False, online: bool | None = None) -> dict[str, Any]:
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


async def build_topology(session: AsyncSession, *, include_clients: bool = True, client_limit: int = 80) -> dict[str, Any]:
    """Return vis-network compatible nodes/edges plus raw meta for the admin map."""
    static = deepcopy(await topology_store.get_document(session))
    nodes_raw = deepcopy(static.get("nodes") or [])
    links = static.get("links") or []
    node_ids = {n["id"] for n in nodes_raw}

    devices: list[models.Device] = []
    sessions: list[models.RadAcct] = []
    if include_clients:
        devices = list(
            await session.scalars(
                select(models.Device)
                .where(models.Device.online.is_(True))
                .order_by(models.Device.last_seen.desc())
                .limit(client_limit)
            )
        )
        sessions = list(
            await session.scalars(
                select(models.RadAcct)
                .where(models.RadAcct.acctstoptime.is_(None))
                .order_by(models.RadAcct.acctstarttime.desc())
                .limit(50)
            )
        )

    # Attach live counts to AP / server nodes.
    ap_counts: dict[str, int] = {}
    for d in devices:
        if d.type in ("router", "ap"):
            continue
        ap_id = _resolve_ap_id(static, d.source_ap)
        ap_counts[ap_id] = ap_counts.get(ap_id, 0) + 1

    vis_nodes = []
    for n in nodes_raw:
        vn = _vis_node(n)
        if n["id"] in ap_counts:
            vn["label"] = f"{n.get('label', n['id'])} ({ap_counts[n['id']]} clients)"
        vis_nodes.append(vn)

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

    # Dynamic client nodes (end-user devices) hang off their AP.
    offset_idx = 0
    for d in devices:
        if d.type in ("router", "ap"):
            continue
        cid = f"client-{d.mac_address.replace(':', '')}"
        ap_id = _resolve_ap_id(static, d.source_ap)
        if ap_id not in node_ids:
            ap_id = static.get("client_attachment", {}).get("default_ap", "ap-bldg-b-1")
        angle = (offset_idx % 12) * 0.52
        offset_idx += 1
        ap_node = next((x for x in nodes_raw if x["id"] == ap_id), None)
        base_x = (ap_node or {}).get("fixed", {}).get("x", 400)
        base_y = (ap_node or {}).get("fixed", {}).get("y", 600)
        client_node = {
            "id": cid,
            "label": (d.hostname or d.vendor or "Client")[:18],
            "kind": "client",
            "zone": ap_node.get("zone", "guest") if ap_node else "guest",
            "mac": d.mac_address,
            "ip": d.ip_address,
            "vendor": d.vendor,
            "fixed": {"x": base_x + 40 * (offset_idx % 5 - 2), "y": base_y + 55 + (offset_idx // 5) * 28},
        }
        vis_nodes.append(_vis_node(client_node, dynamic=True, online=True))
        vis_edges.append(
            {
                "id": f"lk-{cid}",
                "from": ap_id,
                "to": cid,
                "label": "Wi‑Fi",
                "dashes": True,
                "color": {"color": "#22c55e"},
                "arrows": "to",
            }
        )

    # Active RADIUS sessions → session nodes on the server.
    for i, s in enumerate(sessions):
        sid = f"session-{s.radacctid}"
        vis_nodes.append(
            _vis_node(
                {
                    "id": sid,
                    "label": s.username[:12] if s.username else "user",
                    "kind": "session",
                    "zone": "guest",
                    "ip": s.framedipaddress,
                    "mac": s.callingstationid or s.calledstationid,
                    "fixed": {"x": 900 + (i % 4) * 35, "y": 320 + (i // 4) * 30},
                },
                dynamic=True,
                online=True,
            )
        )
        vis_edges.append(
            {
                "id": f"lk-{sid}",
                "from": "srv-zyranet",
                "to": sid,
                "label": "RADIUS",
                "dashes": True,
                "color": {"color": "#fbbf24"},
                "arrows": "to",
            }
        )

    switch_port_map: dict[str, list[dict[str, Any]]] = {}
    for link in links:
        for end, port_key in ((link.get("source"), "source_port"), (link.get("target"), "target_port")):
            if not end or not link.get(port_key):
                continue
            node = next((n for n in nodes_raw if n["id"] == end and n.get("kind") == "switch"), None)
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
            "online_clients": len([d for d in devices if d.type not in ("router", "ap")]),
            "active_sessions": len(sessions),
            "links": len(vis_edges),
        },
    }
