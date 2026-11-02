"""Read-only hardware adapter contracts and the generic SNMP identity adapter."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from .snmp_discover import SnmpTarget

SYS_NAME = "1.3.6.1.2.1.1.5.0"
SYS_DESCR = "1.3.6.1.2.1.1.1.0"
SYS_OBJECT_ID = "1.3.6.1.2.1.1.2.0"
SYS_UPTIME = "1.3.6.1.2.1.1.3.0"
_INSPECTION_LIMIT = asyncio.Semaphore(4)


@dataclass(frozen=True)
class AdapterCapability:
    name: str
    access: str
    description: str


@dataclass(frozen=True)
class HardwareIdentity:
    adapter: str
    protocol: str
    host: str
    sys_name: str | None
    sys_descr: str | None
    sys_object_id: str | None
    sys_uptime_ticks: int | None
    collected_at: datetime


class HardwareAdapter(Protocol):
    adapter_id: str
    display_name: str
    protocol: str
    capabilities: tuple[AdapterCapability, ...]

    async def inspect(
        self, target: SnmpTarget, *, timeout: float, retries: int
    ) -> HardwareIdentity: ...


class SnmpReadOnlyAdapter:
    adapter_id = "generic-snmp-v2c"
    display_name = "Generic SNMPv2c read-only"
    protocol = "snmp-v2c"
    capabilities = (
        AdapterCapability("identify", "read", "Read sysName, sysDescr, sysObjectID and sysUpTime."),
        AdapterCapability("inspect", "read", "Read standard system identity fields."),
    )

    async def inspect(
        self, target: SnmpTarget, *, timeout: float, retries: int
    ) -> HardwareIdentity:
        async with _INSPECTION_LIMIT:
            return await self._inspect_limited(target, timeout=timeout, retries=retries)

    async def _inspect_limited(
        self, target: SnmpTarget, *, timeout: float, retries: int
    ) -> HardwareIdentity:
        try:
            from pysnmp.hlapi.v1arch.asyncio import (  # type: ignore
                CommunityData,
                SnmpDispatcher,
                UdpTransportTarget,
                get_cmd,
            )
        except ImportError as exc:
            raise RuntimeError("PySNMP 7.1 is required for SNMP inspection") from exc

        oids = (SYS_NAME, SYS_DESCR, SYS_OBJECT_ID, SYS_UPTIME)
        with SnmpDispatcher() as dispatcher:
            transport = await UdpTransportTarget.create(
                (target.host, target.port), timeout=timeout, retries=retries
            )
            error, status, index, var_binds = await get_cmd(
                dispatcher,
                CommunityData(target.community, mpModel=1),
                transport,
                *((oid, None) for oid in oids),
            )

        if error:
            raise RuntimeError(str(error))
        if status:
            failed_oid = var_binds[int(index) - 1][0] if index else "?"
            raise RuntimeError(f"SNMP {status} at {failed_oid}")

        values = {str(oid): value for oid, value in var_binds}
        uptime_raw = values.get(SYS_UPTIME)
        try:
            uptime = int(uptime_raw) if uptime_raw is not None else None
        except (TypeError, ValueError):
            uptime = None

        return HardwareIdentity(
            adapter=self.adapter_id,
            protocol=self.protocol,
            host=target.host,
            sys_name=_meaningful(values.get(SYS_NAME)),
            sys_descr=_meaningful(values.get(SYS_DESCR)),
            sys_object_id=_meaningful(values.get(SYS_OBJECT_ID)),
            sys_uptime_ticks=uptime,
            collected_at=datetime.now(UTC),
        )


def _meaningful(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    marker = text.lower().replace(" ", "").replace("_", "")
    if not text or marker.startswith(("nosuchobject", "nosuchinstance", "endofmibview")):
        return None
    return text


SNMP_READ_ONLY = SnmpReadOnlyAdapter()
ADAPTERS: tuple[HardwareAdapter, ...] = (SNMP_READ_ONLY,)


def adapter_catalog() -> list[dict[str, object]]:
    """Describe executable adapter support without implying vendor support."""
    return [
        {
            "id": adapter.adapter_id,
            "name": adapter.display_name,
            "protocol": adapter.protocol,
            "vendor_scope": "standard SNMP system MIB only; vendor-specific support unverified",
            "capabilities": [
                {
                    "name": capability.name,
                    "access": capability.access,
                    "description": capability.description,
                }
                for capability in adapter.capabilities
            ],
        }
        for adapter in ADAPTERS
    ]
