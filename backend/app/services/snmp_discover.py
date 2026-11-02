"""SNMP LLDP neighbor discovery for managed switches.

Hardened for unattended operation: configurable timeouts/retries, bounded
concurrency across targets, per-target timing and error classification, and
de-duplicated link suggestions (no self-links).
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any

from ..config import get_settings

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

_ERROR_CLASSES = (
    ("timeout", ("timeout", "timed out")),
    ("auth", ("authorization", "community", "permission", "unknown snmp version")),
    (
        "unreachable",
        ("unreachable", "no route", "socket", "getaddrinfo", "name or service", "refused"),
    ),
)


def classify_error(message: str | None) -> str:
    """Map a raw SNMP failure message onto a stable error class."""
    msg = (message or "").lower()
    for name, needles in _ERROR_CLASSES:
        if any(n in msg for n in needles):
            return name
    return "error"


@dataclass
class SnmpTarget:
    host: str
    community: str = ""
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
    error_class: str | None = None
    duration_ms: float = 0.0
    neighbors: list[LldpNeighbor] = field(default_factory=list)
    interface_up: list[str] = field(default_factory=list)


def _parse_targets(raw: str, *, default_community: str = "") -> list[SnmpTarget]:
    if not raw.strip():
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return [
            SnmpTarget(host=h.strip(), community=default_community)
            for h in raw.split(",")
            if h.strip()
        ]
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


def _snmp_walk_sync(
    host: str,
    community: str,
    oid: str,
    port: int = 161,
    *,
    timeout: float = 2.0,
    retries: int = 1,
) -> dict[str, str]:
    """Bounded thread bridge retained for the synchronous target parser.

    PySNMP removed its synchronous high-level API in 6.2. This bridge runs the
    supported asyncio API in the target's worker thread; ``discover_all_async``
    bounds how many such threads can operate at once.
    """
    return asyncio.run(
        _snmp_walk_async(
            host,
            community,
            oid,
            port,
            timeout=timeout,
            retries=retries,
        )
    )


async def _snmp_walk_async(
    host: str,
    community: str,
    oid: str,
    port: int = 161,
    *,
    timeout: float = 2.0,
    retries: int = 1,
) -> dict[str, str]:
    """Walk one numeric OID subtree using the supported PySNMP asyncio API."""
    try:
        from pysnmp.hlapi.v1arch.asyncio import (  # type: ignore
            CommunityData,
            ObjectIdentity,
            ObjectType,
            SnmpDispatcher,
            UdpTransportTarget,
            walk_cmd,
        )
    except ImportError as exc:
        raise RuntimeError("install the supported PySNMP release: pysnmp>=7.1,<8") from exc

    prefix = oid.rstrip(".") + "."
    results: dict[str, str] = {}
    with SnmpDispatcher() as dispatcher:
        target = await UdpTransportTarget.create(
            (host, port), timeout=timeout, retries=retries
        )
        async for err_ind, err_stat, _err_idx, var_binds in walk_cmd(
            dispatcher,
            CommunityData(community, mpModel=1),
            target,
            ObjectType(ObjectIdentity(oid)),
            lexicographicMode=False,
            maxRows=4096,
        ):
            if err_ind:
                raise RuntimeError(str(err_ind))
            if err_stat:
                raise RuntimeError(str(err_stat))
            for vb in var_binds:
                key = str(vb[0])
                if not key.startswith(prefix):
                    return results
                results[key] = str(vb[1])
    return results


def _index_tail(oid_key: str, base_oid: str) -> str:
    prefix = base_oid + "."
    if oid_key.startswith(prefix):
        return oid_key[len(prefix) :]
    return oid_key.rsplit(".", 1)[-1]


def _discover_one(
    target: SnmpTarget, *, timeout: float = 2.0, retries: int = 1
) -> DiscoveryResult:
    result = DiscoveryResult(target=target, ok=True)
    started = time.perf_counter()
    try:
        if not target.community:
            raise RuntimeError("SNMP community is not configured")
        sys_names = _snmp_walk_sync(
            target.host, target.community, LLDP_REM_SYS_NAME, target.port,
            timeout=timeout, retries=retries,
        )
        port_descs = _snmp_walk_sync(
            target.host, target.community, LLDP_REM_PORT_DESC, target.port,
            timeout=timeout, retries=retries,
        )
        loc_ports = _snmp_walk_sync(
            target.host, target.community, LLDP_LOC_PORT_DESC, target.port,
            timeout=timeout, retries=retries,
        )

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
            if_names = _snmp_walk_sync(
                target.host, target.community, IF_NAME, target.port,
                timeout=timeout, retries=retries,
            )
            if_oper = _snmp_walk_sync(
                target.host, target.community, IF_OPER_STATUS, target.port,
                timeout=timeout, retries=retries,
            )
            for k, name in if_names.items():
                idx = _index_tail(k, IF_NAME)
                if if_oper.get(f"{IF_OPER_STATUS}.{idx}") == "1":
                    result.interface_up.append(name)
    except Exception as exc:
        result.ok = False
        result.error = str(exc)
        result.error_class = classify_error(result.error)
        log.warning(
            "SNMP discovery failed for %s (%s): %s", target.host, result.error_class, exc
        )
    finally:
        result.duration_ms = round((time.perf_counter() - started) * 1000, 1)
    return result


def discover_all(
    targets: list[SnmpTarget], *, timeout: float = 2.0, retries: int = 1
) -> list[DiscoveryResult]:
    return [_discover_one(t, timeout=timeout, retries=retries) for t in targets]


async def discover_all_async(
    targets: list[SnmpTarget],
    *,
    timeout: float,
    retries: int,
    max_concurrent: int,
) -> list[DiscoveryResult]:
    """Bounded-parallel discovery: at most `max_concurrent` SNMP sessions."""
    semaphore = asyncio.Semaphore(max(1, max_concurrent))
    loop = asyncio.get_running_loop()

    async def _one(target: SnmpTarget) -> DiscoveryResult:
        async with semaphore:
            return await loop.run_in_executor(
                None, lambda: _discover_one(target, timeout=timeout, retries=retries)
            )

    return list(await asyncio.gather(*(_one(t) for t in targets)))


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def match_node_id(
    document: dict[str, Any], remote_name: str, remote_ip: str | None = None
) -> str | None:
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
    """Turn LLDP neighbors into link payloads for topology_store.apply_discovered_links.

    Self-links (a node reporting itself) and duplicate (source, target, ports)
    suggestions are dropped before they reach the store.
    """
    suggestions: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()
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
            if not target_id or target_id == source_id:
                continue
            source_port = nb.local_port
            target_port = nb.remote_port_desc or "LLDP"
            key = (source_id, target_id, source_port, target_port)
            if key in seen:
                continue
            seen.add(key)
            suggestions.append(
                {
                    "source": source_id,
                    "target": target_id,
                    "source_port": source_port,
                    "target_port": target_port,
                    "medium": "ethernet",
                    "label": "LLDP",
                    "discovered": True,
                }
            )
    return suggestions


async def run_discovery(
    raw_targets: str,
    document: dict[str, Any],
    *,
    default_community: str | None = None,
    timeout: float | None = None,
    retries: int | None = None,
    max_concurrent: int | None = None,
) -> dict[str, Any]:
    """Run LLDP discovery across all configured targets (structured result)."""
    s = get_settings()
    targets = _parse_targets(
        raw_targets, default_community=default_community or s.snmp_community
    )
    if not targets:
        return {
            "ok": False,
            "error": "no_snmp_targets",
            "results": [],
            "suggestions": [],
            "summary": {"targets": 0, "succeeded": 0, "failed": 0, "duration_ms": 0.0},
        }
    started = time.perf_counter()
    results = await discover_all_async(
        targets,
        timeout=s.snmp_timeout if timeout is None else timeout,
        retries=s.snmp_retries if retries is None else retries,
        max_concurrent=s.snmp_max_concurrent if max_concurrent is None else max_concurrent,
    )
    suggestions = suggest_links(document, results)
    failed = sum(1 for r in results if not r.ok)
    return {
        "ok": failed < len(results),
        "results": [
            {
                "host": r.target.host,
                "node_id": r.target.node_id,
                "ok": r.ok,
                "error": r.error,
                "error_class": r.error_class,
                "duration_ms": r.duration_ms,
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
        "summary": {
            "targets": len(results),
            "succeeded": len(results) - failed,
            "failed": failed,
            "duration_ms": round((time.perf_counter() - started) * 1000, 1),
        },
    }
