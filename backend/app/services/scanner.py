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
import os
import re
import struct
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models
from ..config import get_settings

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
            import time

            with socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP) as sock:
                timeout = 0.3
                sock.settimeout(timeout)
                identifier = (os.getpid() ^ int(time.monotonic() * 1000)) & 0xFFFF
                sequence = 1
                payload = b"zyranet-probe"
                header = struct.pack("!BBHHH", 8, 0, 0, identifier, sequence)
                packet = header + payload
                checksum = _icmp_checksum(packet)
                packet = struct.pack("!BBHHH", 8, 0, checksum, identifier, sequence) + payload
                started = time.monotonic()
                sock.sendto(packet, (ip, 0))
                while time.monotonic() - started < timeout:
                    try:
                        data, address = sock.recvfrom(512)
                    except TimeoutError:
                        return False
                    if address[0] != ip:
                        continue
                    # Linux raw IPv4 sockets include the IPv4 header.
                    if len(data) >= 20 and data[0] >> 4 == 4:
                        header_length = (data[0] & 0x0F) * 4
                        data = data[header_length:]
                    if len(data) < 8:
                        continue
                    icmp_type, code, _checksum, reply_id, reply_sequence = struct.unpack(
                        "!BBHHH", data[:8]
                    )
                    if (icmp_type, code, reply_id, reply_sequence) == (0, 0, identifier, sequence):
                        return True
                return False
        except OSError:
            pass  # fall through to TCP probe
    return False


def _icmp_checksum(packet: bytes) -> int:
    """Compute the Internet checksum for an ICMP packet."""
    if len(packet) % 2:
        packet += b"\x00"
    words = struct.unpack(f"!{len(packet) // 2}H", packet)
    total = sum(words)
    total = (total & 0xFFFF) + (total >> 16)
    total = (total & 0xFFFF) + (total >> 16)
    return (~total) & 0xFFFF


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
def expand_networks(
    cidrs: list[str], max_hosts_per_subnet: int = 1024, max_hosts_total: int = 4096
) -> list[str]:
    """Expand approved CIDRs into a bounded, de-duplicated host list."""
    if max_hosts_per_subnet < 1 or max_hosts_total < 1:
        raise ValueError("discovery host limits must be positive")
    hosts: list[str] = []
    seen: set[str] = set()
    for cidr in cidrs:
        if len(hosts) >= max_hosts_total:
            log.warning("configured discovery ranges exceed total cap of %d hosts", max_hosts_total)
            break
        try:
            net = ipaddress.ip_network(cidr, strict=False)
        except ValueError:
            log.warning("bad CIDR %r, skipping", cidr)
            continue
        if net.version != 4:
            log.warning("IPv6 discovery is not supported yet; skipping %s", cidr)
            continue
        address_count = (
            net.num_addresses if net.prefixlen >= 31 else net.num_addresses - 2
        )
        if address_count > max_hosts_per_subnet:
            log.warning(
                "skipping subnet %s: %d hosts exceeds discovery cap of %d; "
                "split it into approved smaller ranges",
                cidr,
                address_count,
                max_hosts_per_subnet,
            )
            continue
        for host in net.hosts():
            if host not in seen:
                seen.add(host)
                hosts.append(host)
                if len(hosts) >= max_hosts_total:
                    break
    return hosts


def _scope_warnings(
    cidrs: list[str], max_hosts_per_subnet: int, max_hosts_total: int
) -> list[str]:
    """Explain scope entries omitted by the same limits used during expansion."""
    warnings: list[str] = []
    eligible_addresses: set[ipaddress.IPv4Address] = set()
    for cidr in cidrs:
        try:
            net = ipaddress.ip_network(cidr, strict=False)
        except ValueError:
            warnings.append(f"Invalid CIDR skipped: {cidr}")
            continue
        if net.version != 4:
            warnings.append(f"IPv6 range skipped (not supported): {cidr}")
            continue
        host_count = (
            net.num_addresses if net.prefixlen >= 31 else max(0, net.num_addresses - 2)
        )
        if host_count > max_hosts_per_subnet:
            warnings.append(f"Range skipped because it exceeds the per-subnet host cap: {cidr}")
            continue
        for address in net.hosts():
            if address in eligible_addresses:
                continue
            eligible_addresses.add(address)
            if len(eligible_addresses) > max_hosts_total:
                break
        if len(eligible_addresses) > max_hosts_total:
            break
    if len(eligible_addresses) > max_hosts_total:
        warnings.append(
            f"Configured ranges exceed the total host cap ({max_hosts_total}); "
            "later targets were omitted."
        )
    if not cidrs:
        warnings.append("No scan CIDRs are configured.")
    return warnings


async def scan(
    session: AsyncSession, cidrs: list[str], *, run_id: int | None = None
) -> dict[str, int | str]:
    """Run a bounded sweep against a new scheduled run or a claimed queued run."""
    settings = get_settings()
    hosts = expand_networks(
        cidrs,
        settings.scan_max_hosts_per_subnet,
        settings.scan_max_hosts_total,
    )
    scope_warnings = _scope_warnings(
        cidrs,
        settings.scan_max_hosts_per_subnet,
        settings.scan_max_hosts_total,
    )
    if run_id is None:
        run = models.DiscoveryRun(
            status="running", scope=cidrs, targets_total=len(hosts), started_at=_now()
        )
        session.add(run)
        await session.flush()
        run_id = run.id
        await session.commit()
    else:
        run = await session.get(models.DiscoveryRun, run_id)
        if run is None or run.status != "running":
            raise ValueError("queued discovery run was not claimed")
        run.targets_total = len(hosts)
        await session.commit()

    try:
        loop = asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=64) as pool:
            results = await asyncio.gather(
                *(loop.run_in_executor(pool, _probe_host_sync, ip) for ip in hosts),
                return_exceptions=True,
            )
        if any(isinstance(result, asyncio.CancelledError) for result in results):
            raise asyncio.CancelledError
        responded_ips = {
            ip for ip, result in zip(hosts, results, strict=True) if result is True
        }
        probe_errors = sum(isinstance(result, Exception) for result in results)

        # The host neighbour table also contains unrelated and cached entries.
        # Ingest only IPs this run was explicitly configured to probe.
        target_ips = set(hosts)
        entries = {
            e.mac.lower(): e
            for e in _arp_table()
            if e.ip in target_ips and e.mac and e.mac != "00:00:00:00:00:00"
        }
        upserted = 0
        for e in entries.values():
            if await _upsert(
                session,
                e,
                run_id=run_id,
                evidence={
                    "neighbor_table": True,
                    "active_probe_replied": e.ip in responded_ips,
                    "probe_method": "icmp_then_tcp_80_443",
                },
            ):
                upserted += 1

        run = await session.get(models.DiscoveryRun, run_id)
        assert run is not None
        run.probes_responded = len(responded_ips)
        run.probe_errors = probe_errors
        run.devices_observed = len(entries)
        run.status = "partial" if probe_errors or scope_warnings else "succeeded"
        if scope_warnings:
            run.error = " ".join(scope_warnings)[:1000]
        run.completed_at = _now()
        await session.commit()
        return {
            "run_id": run_id,
            "status": run.status,
            "targets": len(hosts),
            "probes_responded": len(responded_ips),
            "probe_errors": probe_errors,
            "seen": len(entries),
            "upserted": upserted,
        }
    except asyncio.CancelledError:
        await session.rollback()
        failed_run = await session.get(models.DiscoveryRun, run_id)
        if failed_run is not None:
            failed_run.status = "failed"
            failed_run.error = "scan cancelled"
            failed_run.completed_at = _now()
            await session.commit()
        raise
    except Exception as exc:
        await session.rollback()
        failed_run = await session.get(models.DiscoveryRun, run_id)
        if failed_run is not None:
            failed_run.status = "failed"
            failed_run.error = str(exc)[:1000]
            failed_run.completed_at = _now()
            await session.commit()
        raise


async def enqueue_scan(
    session: AsyncSession, cidrs: list[str], *, requested_by: str
) -> models.DiscoveryRun:
    """Persist a bounded-scope request for the dedicated worker to execute."""
    run = models.DiscoveryRun(
        status="queued",
        scope=list(cidrs),
        requested_by=requested_by,
    )
    session.add(run)
    await session.flush()
    return run


def _now():
    return datetime.now(UTC)


async def _upsert(
    session: AsyncSession,
    entry: SeenDevice,
    *,
    run_id: int | None = None,
    evidence: dict | None = None,
) -> bool:
    mac = entry.mac.lower()
    device = await session.scalar(select(models.Device).where(models.Device.mac_address == mac))
    if device is None:
        device = models.Device(mac_address=mac)
        session.add(device)
        await session.flush()
        new = True
    else:
        new = False

    now = _now()
    device.ip_address = entry.ip or device.ip_address
    device.hostname = entry.hostname or device.hostname
    device.source_ap = entry.ap or device.source_ap
    device.vendor = device.vendor or _vendor_from_mac(mac)
    device.type = _infer_type(device.vendor)
    device.online = entry.online
    device.last_seen = now
    device.updated_at = now

    previous = await session.scalar(
        select(models.DeviceSighting)
        .where(models.DeviceSighting.device_id == device.id)
        .order_by(models.DeviceSighting.seen_at.desc(), models.DeviceSighting.id.desc())
        .limit(1)
    )
    should_record = previous is None or previous.ip_address != entry.ip
    if previous is not None and not should_record:
        previous_seen = previous.seen_at
        if previous_seen.tzinfo is None:
            previous_seen = previous_seen.replace(tzinfo=UTC)
        age = (now - previous_seen).total_seconds()
        should_record = age >= max(60, get_settings().scan_sighting_interval_seconds)

    if should_record:
        session.add(
            models.DeviceSighting(
                device_id=device.id,
                run_id=run_id,
                ip_address=entry.ip,
                source_ap=entry.ap,
                source="neighbor_table",
                evidence=evidence or {"neighbor_table": True},
                online=entry.online,
                seen_at=now,
            )
        )
    return new or device.online
