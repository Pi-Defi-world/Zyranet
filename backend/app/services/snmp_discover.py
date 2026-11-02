"""SNMP LLDP neighbor discovery for managed switches."""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger("zyranet.snmp")

# LLDP-MIB lldpRemTable column OIDs (index = timeMark.localPortNum.remIndex)
LLDP_REM_SYS_NAME = "1.0.8802.1.1.2.1.4.1.1.9"
LLDP_REM_PORT_DESC = "1.0.8802.1.1.2.1.4.1.1.8"
LLDP_REM_PORT_ID = "1.0.8802.1.1.2.1.4.1.1.7"
LLDP_REM_CHASSIS_ID = "1.0.8802.1.1.2.1.4.1.1.5"
LLDP_LOC_PORT_DESC = "1.0.8802.1.1.2.1.3.7.1.4"

# IF-MIB (fallback when LLDP absent)
IF_NAME = "1.3.6.1.2.1.31.1.1.1.18"
IF_OPER_STATUS = "1.3.6.1.2.1.2.2.1.8"


@dataclass
class SnmpTarget:
    host: str
    community: str = "public"
    node_id: str | None = None
    port: int = 161
    version: str = "2c"


@dataclass
class LldpNeighbor:
    local_port: str
    remote_sys_name: str
    remote_port_desc: str = ""
    remote_chassis: str = ""


@dataclass
class DiscoveryResult:
    target: SnmpTarget
    ok: bool
    error: str | None = None
    neighbors: list[LldpNeighbor] = field(default_factory=list)
    interface_up: list[str] = field(default_factory=list)


def _parse_targets(raw: str, *, default_community: str = "public") -> list[SnmpTarget]:
    if not raw.strip():
        return []
    import json

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return [SnmpTarget(host=h.strip(), community=default_community) for h in raw.split(",") if h.strip()]
    out: list[SnmpTarget] = []
    for item in data:
        if isinstance(item, str):
            out.append(SnmpTarget(host=item, community=default_community))
        elif isinstance(item, dict) and item.get("host"):
            out.append(
                SnmpTarget(
                    host=item["host"],
                    community=item.get("community") or default_community,
                    node_id=item.get("node_id"),
                    port=int(item.get("port", 161)),
                    version=item.get("version", "2c"),
                )
            )
    return out


def _snmp_walk_sync(host: str, community: str, oid: str, port: int = 161) -> dict[str, str]:
    try:
        from pysnmp.hlapi import (  # type: ignore
            CommunityData,
            ContextData,
            ObjectIdentity,
            ObjectType,
            SnmpEngine,
            UdpTransportTarget,
            nextCmd,
        )
    except ImportError as exc:
        raise RuntimeError("pysnmp is not installed; pip install pysnmp") from exc

    base = oid if oid.endswith(".") else oid + "."
    results: dict[str, str] = {}
    for err_ind, err_stat, _err_idx, var_binds in nextCmd(
        SnmpEngine(),
        CommunityData(community, mpModel=1),
        UdpTransportTarget((host, port), timeout=2.0, retries=1),
        ContextData(),
        ObjectType(ObjectIdentity(oid)),
        lexicographicMode=False,
    ):
        if err_ind:
            raise RuntimeError(str(err_ind))
        if err_stat:
            raise RuntimeError(err_stat.prettyPrint())
        for vb in var_binds:
            k = str(vb[0])
            if not k.startswith(base.rstrip(".")):
                break
            results[k] = str(vb[1])
    return results


def _index_tail(oid_key: str, base_oid: str) -> str:
    prefix = base_oid + "."
    if oid_key.startswith(prefix):
        return oid_key[len(prefix) :]
    return oid_key.rsplit(".", 1)[-1]


def _discover_one(target: SnmpTarget) -> DiscoveryResult:
    result = DiscoveryResult(target=target, ok=True)
    try:
        sys_names = _snmp_walk_sync(target.host, target.community, LLDP_REM_SYS_NAME, target.port)
        port_descs = _snmp_walk_sync(target.host, target.community, LLDP_REM_PORT_DESC, target.port)
        loc_ports = _snmp_walk_sync(target.host, target.community, LLDP_LOC_PORT_DESC, target.port)

        # Group by remIndex suffix (timeMark.localPortNum.remIndex)
        by_rem: dict[str, dict[str, str]] = {}
        for k, v in sys_names.items():
            idx = _index_tail(k, LLDP_REM_SYS_NAME)
            by_rem.setdefault(idx, {})["sys_name"] = v
        for k, v in port_descs.items():
            idx = _index_tail(k, LLDP_REM_PORT_DESC)
            by_rem.setdefault(idx, {})["port_desc"] = v

        loc_by_num: dict[str, str] = {}
        for k, v in loc_ports.items():
            tail = _index_tail(k, LLDP_LOC_PORT_DESC)
            loc_by_num[tail] = v

        for idx, fields in by_rem.items():
            parts = idx.split(".")
            local_num = parts[1] if len(parts) >= 2 else parts[0]
            local_port = loc_by_num.get(local_num, local_num)
            result.neighbors.append(
                LldpNeighbor(
                    local_port=str(local_port),
                    remote_sys_name=fields.get("sys_name", ""),
                    remote_port_desc=fields.get("port_desc", ""),
                )
            )

        if not result.neighbors:
            if_names = _snmp_walk_sync(target.host, target.community, IF_NAME, target.port)
            if_oper = _snmp_walk_sync(target.host, target.community, IF_OPER_STATUS, target.port)
            for k, name in if_names.items():
                idx = _index_tail(k, IF_NAME)
                if if_oper.get(f"{IF_OPER_STATUS}.{idx}") == "1":
                    result.interface_up.append(name)
    except Exception as exc:
        result.ok = False
        result.error = str(exc)
        log.warning("SNMP discovery failed for %s: %s", target.host, exc)
    return result


def discover_all(targets: list[SnmpTarget]) -> list[DiscoveryResult]:
    return [_discover_one(t) for t in targets]


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def match_node_id(document: dict[str, Any], remote_name: str, remote_ip: str | None = None) -> str | None:
    nodes = document.get("nodes") or []
    rn = _norm(remote_name)
    for n in nodes:
        if rn and rn in _norm(n.get("label", "")):
            return n["id"]
        if rn and rn in _norm(n.get("id", "")):
            return n["id"]
        if remote_ip and n.get("mgmt_ip") == remote_ip:
            return n["id"]
    return None


def suggest_links(
    document: dict[str, Any],
    results: list[DiscoveryResult],
) -> list[dict[str, Any]]:
    """Turn LLDP neighbors into link payloads for topology_store.apply_discovered_links."""
    suggestions: list[dict[str, Any]] = []
    for res in results:
        if not res.ok:
            continue
        source_id = res.target.node_id
        if not source_id:
            source_id = match_node_id(document, res.target.host) or match_node_id(
                document, res.target.host.replace(".", "-")
            )
        if not source_id:
            for n in document.get("nodes") or []:
                if n.get("mgmt_ip") == res.target.host:
                    source_id = n["id"]
                    break
        if not source_id:
            continue
        for nb in res.neighbors:
            if not nb.remote_sys_name:
                continue
            target_id = match_node_id(document, nb.remote_sys_name)
            if not target_id:
                continue
            local_port = nb.local_port
            if local_port.isdigit():
                source_port = local_port
            else:
                source_port = local_port
            suggestions.append(
                {
                    "source": source_id,
                    "target": target_id,
                    "source_port": source_port,
                    "target_port": nb.remote_port_desc or "LLDP",
                    "medium": "ethernet",
                    "label": "LLDP",
                    "discovered": True,
                }
            )
    return suggestions


async def run_discovery(
    raw_targets: str, document: dict[str, Any], *, default_community: str = "public"
) -> dict[str, Any]:
    targets = _parse_targets(raw_targets, default_community=default_community)
    if not targets:
        return {"ok": False, "error": "no_snmp_targets", "results": [], "suggestions": []}
    loop = asyncio.get_running_loop()
    results = await loop.run_in_executor(None, discover_all, targets)
    suggestions = suggest_links(document, results)
    return {
        "ok": True,
        "results": [
            {
                "host": r.target.host,
                "node_id": r.target.node_id,
                "ok": r.ok,
                "error": r.error,
                "neighbors": [
                    {
                        "local_port": n.local_port,
                        "remote_sys_name": n.remote_sys_name,
                        "remote_port_desc": n.remote_port_desc,
                    }
                    for n in r.neighbors
                ],
                "interfaces_up": r.interface_up[:40],
            }
            for r in results
        ],
        "suggestions": suggestions,
    }
