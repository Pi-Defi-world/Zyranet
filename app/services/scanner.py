"""Network device discovery + tracking.

Scans configured subnets, resolves MAC -> vendor via OUI, and upserts devices
into the `devices` / `device_sightings` tables.

Sources used, in order of reliability:
  1. The OS neighbour/ARP cache  (Linux `/proc/net/arp`, else `arp -a`).
  2. An active probe to populate that cache (ICMP echo if we have a raw socket;
     otherwise a fast TCP-connect packet to common ports).
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import ipaddress
import logging
import re
import subprocess
import sys
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models

log = logging.getLogger("zyranet.scanner")

# Vendors OUI database (manuf) is lazy-loaded the first time it is used.
_manuf = None

_TCP_PORTS = (80, 443)


def _get_manuf():
    global _manuf
    if _manuf is None:
        try:
            from manuf import manuf  # type: ignore

            _manuf = manuf.MacParser()
        except Exception as exc:  # pragma: no cover - optional dependency
            log.warning("manuf unavailable, vendor lookup disabled: %s", exc)
            _manuf = False
    return _manuf or None


def _vendor_from_mac(mac: str) -> str | None:
    parser = _get_manuf()
    if parser is None:
        return None
    try:
        return parser.get_manuf(mac)
    except Exception:
        return None


_AP_VENDORS = (
    "tp-link", "ubiquiti", "ubnt", "mikrotik", "cisco", "netgear", "tenda", "huawei", "zyxel"
)
_PHONE_VENDORS = (
    "apple", "samsung", "xiaomi", "huawei", "oppo", "vivo", "tecno", "infinix", "oneplus", "google"
)
_COMPUTER_VENDORS = ("dell", "hp ", "lenovo", "acer", "asus", "msi", "intel", "apple")


def _infer_type(vendor: str | None) -> str:
    v = (vendor or "").lower()
    if any(k in v for k in _AP_VENDORS):
        return "ap"
    if any(k in v for k in _PHONE_VENDORS):
        return "phone"
    if any(k in v for k in _COMPUTER_VENDORS):
        return "computer"
    return "unknown"


@dataclass
class SeenDevice:
    mac: str
    ip: str | None
    hostname: str | None = None
    ap: str | None = None
    online: bool = True


# ---------------------------------------------------------------------------
# ARP / neighbour table parsing
# ---------------------------------------------------------------------------
def _linux_arp() -> list[SeenDevice]:
    try:
        raw = open("/proc/net/arp", encoding="utf-8").readlines()[1:]
    except OSError:
        return []
    out: list[SeenDevice] = []
    for line in raw:
        cols = line.split()
        if len(cols) >= 4 and cols[2] not in ("0x0", "0x1"):
            out.append(SeenDevice(mac=cols[3], ip=cols[0]))
    return out


def _windows_arp() -> list[SeenDevice]:
    try:
        raw = subprocess.run(["arp", "-a"], capture_output=True, text=True, timeout=20).stdout
    except Exception:
        return []
    out: list[SeenDevice] = []
    for line in raw.splitlines():
        m = re.search(r"(\d{1,3}(?:\.\d{1,3}){3})\s+([0-9a-fA-F-]{17})", line)
        if m:
            out.append(SeenDevice(mac=m.group(2).replace("-", ":").lower(), ip=m.group(1)))
    return out


def _arp_table() -> list[SeenDevice]:
    if sys.platform.startswith("linux"):
        return _linux_arp()
    return _windows_arp()


# ---------------------------------------------------------------------------
# Active probing to populate the ARP cache.
# These use BLOCKING sockets (ICMP raw + TCP connect), so they are run in a
# thread executor to keep the event loop responsive during a scan.
# ---------------------------------------------------------------------------
def _ping_one_sync(ip: str) -> bool:
    """Best-effort ICMP echo; returns True if the host answered."""
    if sys.platform.startswith("linux"):
        try:
            import socket

            with socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP) as sock:
                sock.settimeout(0.3)
                sock.sendto(b"\x08\x00\x00\x00\x00\x00\x00\x00", (ip, 0))
                try:
                    sock.recvfrom(256)
                    return True
                except TimeoutError:
                    return False
        except OSError:
            pass  # fall through to TCP probe
    return False


def _tcp_probe_sync(ip: str, timeout: float = 0.3) -> bool:
    import socket

    for port in _TCP_PORTS:
        try:
            with socket.create_connection((ip, port), timeout=timeout):
                return True
        except OSError:
            continue
    return False


def _probe_host_sync(ip: str) -> bool:
    if _ping_one_sync(ip):
        return True
    return _tcp_probe_sync(ip)


async def probe_host(ip: str) -> bool:
    """Host up-check (ICMP then TCP fallback). Offloads blocking I/O to a thread."""
    return await asyncio.to_thread(_probe_host_sync, ip)


# ---------------------------------------------------------------------------
# Discovery orchestrator
# ---------------------------------------------------------------------------
def expand_networks(cidrs: list[str]) -> list[str]:
    hosts: list[str] = []
    for cidr in cidrs:
        try:
            net = ipaddress.ip_network(cidr, strict=False)
        except ValueError:
            log.warning("bad CIDR %r, skipping", cidr)
            continue
        if net.num_addresses > 1024:  # cap sweep size; ARP table still covers rest
            log.info("subnet %s too large, capping sweep: %s", cidr, net.num_addresses)
        hosts.extend(str(h) for h in net.hosts())
    return hosts


async def scan(session: AsyncSession, cidrs: list[str]) -> dict[str, int]:
    """Run a discovery sweep, upsert devices, return a summary."""
    hosts = expand_networks(cidrs)
    loop = asyncio.get_running_loop()
    # Thread pool for the blocking ICMP/TCP probes.
    with concurrent.futures.ThreadPoolExecutor(max_workers=64) as pool:
        await asyncio.gather(
            *(loop.run_in_executor(pool, _probe_host_sync, ip) for ip in hosts),
            return_exceptions=True,
        )

    # Now read whatever the OS resolved.
    entries = {e.mac.lower(): e for e in _arp_table()}
    # Also fold in the probed hosts we know replied (IP-mapped via cache only).
    upserted = 0
    for e in entries.values():
        if not e.mac or e.mac == "00:00:00:00:00:00":
            continue
        if await _upsert(session, e):
            upserted += 1
    await session.commit()
    return {"seen": len(entries), "upserted": upserted}


async def _upsert(session: AsyncSession, entry: SeenDevice) -> bool:
    mac = entry.mac.lower()
    device = await session.scalar(select(models.Device).where(models.Device.mac_address == mac))
    if device is None:
        device = models.Device(mac_address=mac)
        session.add(device)
        await session.flush()
        new = True
    else:
        new = False

    from datetime import UTC, datetime

    now = datetime.now(UTC)
    device.ip_address = entry.ip or device.ip_address
    device.hostname = entry.hostname or device.hostname
    device.source_ap = entry.ap or device.source_ap
    device.vendor = device.vendor or _vendor_from_mac(mac)
    device.type = _infer_type(device.vendor)
    device.online = entry.online
    device.last_seen = now
    device.updated_at = now

    session.add(
        models.DeviceSighting(
            device_id=device.id,
            ip_address=entry.ip,
            source_ap=entry.ap,
            online=entry.online,
            seen_at=now,
        )
    )
    return new or device.online
