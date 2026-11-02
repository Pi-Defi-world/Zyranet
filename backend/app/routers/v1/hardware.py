"""Safe, read-only hardware adapter inventory and inspection operations."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ... import models, schemas
from ...config import get_settings
from ...db import get_session
from ...security import Principal, require_role
from ...services.adapters import SNMP_READ_ONLY, adapter_catalog
from ...services.audit import record_request_audit
from ...services.snmp_discover import _parse_targets, classify_error

router = APIRouter(tags=["hardware adapters"])
READ = Depends(require_role("viewer"))
WRITE = Depends(require_role("operator"))


@router.get("/adapters", response_model=list[schemas.AdapterDescriptorOut])
async def list_adapters(_: Principal = READ):
    return adapter_catalog()


@router.post(
    "/devices/{device_id}/inspect",
    response_model=schemas.HardwareIdentityOut,
    dependencies=[WRITE],
)
async def inspect_device(
    device_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_role("operator")),
):
    """Read standard system identity from one explicitly configured SNMP target."""
    settings = get_settings()
    if not settings.snmp_enabled:
        raise HTTPException(status.HTTP_409_CONFLICT, "SNMP inspection is disabled")

    device = await session.get(models.Device, device_id)
    if device is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "device not found")
    if not device.ip_address:
        raise HTTPException(status.HTTP_409_CONFLICT, "device has no current IP address")

    targets = _parse_targets(settings.snmp_targets, default_community=settings.snmp_community)
    target = next((item for item in targets if item.host == device.ip_address), None)
    if target is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "device address is not in the explicitly configured SNMP target list",
        )
    if not target.community:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "SNMP community is not configured for this target",
        )

    try:
        identity = await SNMP_READ_ONLY.inspect(
            target,
            timeout=settings.snmp_timeout,
            retries=settings.snmp_retries,
        )
    except Exception as exc:
        error_class = classify_error(str(exc))
        await record_request_audit(
            session,
            request,
            actor=principal.username,
            role=principal.role,
            action="device.inspect",
            entity_type="device",
            entity_id=device.id,
            outcome="failure",
            detail={"adapter": SNMP_READ_ONLY.adapter_id, "error_class": error_class},
        )
        await session.commit()
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            f"SNMP inspection failed ({error_class})",
        ) from exc

    await record_request_audit(
        session,
        request,
        actor=principal.username,
        role=principal.role,
        action="device.inspect",
        entity_type="device",
        entity_id=device.id,
        detail={
            "adapter": identity.adapter,
            "protocol": identity.protocol,
            "host": identity.host,
            "sys_name": identity.sys_name[:255] if identity.sys_name else None,
            "sys_object_id": identity.sys_object_id[:255] if identity.sys_object_id else None,
        },
    )
    await session.commit()
    return identity
