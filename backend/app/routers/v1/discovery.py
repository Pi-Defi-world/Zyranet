"""Discovery run control and read APIs for persisted probe evidence."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import case, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ... import models, schemas
from ...config import get_settings
from ...db import get_session
from ...security import Principal, require_role
from ...services import scanner
from ...services.audit import record_request_audit

router = APIRouter(prefix="/discovery", tags=["discovery"])
READ = Depends(require_role("viewer"))
WRITE = Depends(require_role("operator"))


@router.post(
    "/runs",
    response_model=schemas.DiscoveryRunOut,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[WRITE],
)
async def enqueue_run(
    request: Request,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_role("operator")),
):
    settings = get_settings()
    if not settings.discovery_ready:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "discovery requires enablement and approved scan CIDRs",
        )
    try:
        run = await scanner.enqueue_scan(
            session,
            settings.scan_cidr_list,
            requested_by=principal.username,
        )
        await record_request_audit(
            session,
            request,
            actor=principal.username,
            role=principal.role,
            action="discovery.run.enqueue",
            entity_type="discovery_run",
            entity_id=run.id,
            detail={"scope": run.scope},
        )
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "another discovery run is already queued or running",
        ) from exc
    await session.refresh(run)
    return run


@router.get("/overview", response_model=schemas.OverviewSummaryOut)
async def overview(
    session: AsyncSession = Depends(get_session),
    _: Principal = READ,
):
    cutoff = datetime.now(UTC) - timedelta(
        seconds=max(60, get_settings().device_stale_after_seconds)
    )
    counts = await session.execute(
        select(
            func.count(models.Device.id),
            func.sum(
                case(
                    (models.Device.online.is_(True) & (models.Device.last_seen >= cutoff), 1),
                    else_=0,
                )
            ),
            func.sum(
                case(
                    (models.Device.online.is_(True) & (models.Device.last_seen < cutoff), 1),
                    else_=0,
                )
            ),
            func.sum(case((models.Device.online.is_(False), 1), else_=0)),
        )
    )
    devices, observed, stale, unknown = counts.one()
    locations = int(await session.scalar(select(func.count()).select_from(models.Location)) or 0)
    latest = await session.scalar(
        select(models.DiscoveryRun)
        .order_by(models.DiscoveryRun.created_at.desc(), models.DiscoveryRun.id.desc())
        .limit(1)
    )
    return schemas.OverviewSummaryOut(
        devices=int(devices or 0),
        observed_devices=int(observed or 0),
        stale_devices=int(stale or 0),
        unknown_devices=int(unknown or 0),
        locations=locations,
        latest_discovery=schemas.DiscoveryRunOut.model_validate(latest) if latest else None,
    )


@router.get("/runs", response_model=schemas.DiscoveryRunPageOut)
async def list_runs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
    _: Principal = READ,
):
    total = int(await session.scalar(select(func.count()).select_from(models.DiscoveryRun)) or 0)
    rows = await session.scalars(
        select(models.DiscoveryRun)
        .order_by(models.DiscoveryRun.created_at.desc(), models.DiscoveryRun.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return schemas.DiscoveryRunPageOut(
        total=total,
        items=[schemas.DiscoveryRunOut.model_validate(row) for row in rows],
    )


@router.get("/runs/{run_id}", response_model=schemas.DiscoveryRunOut)
async def get_run(
    run_id: int,
    session: AsyncSession = Depends(get_session),
    _: Principal = READ,
):
    run = await session.get(models.DiscoveryRun, run_id)
    if run is None:
        raise HTTPException(404, "discovery run not found")
    return run


@router.get(
    "/runs/{run_id}/observations",
    response_model=schemas.DiscoveryObservationPageOut,
)
async def list_run_observations(
    run_id: int,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
    _: Principal = READ,
) -> dict[str, Any]:
    if await session.get(models.DiscoveryRun, run_id) is None:
        raise HTTPException(404, "discovery run not found")

    base = (
        select(models.DeviceSighting, models.Device)
        .join(models.Device, models.Device.id == models.DeviceSighting.device_id)
        .where(models.DeviceSighting.run_id == run_id)
    )
    total = int(
        await session.scalar(
            select(func.count())
            .select_from(models.DeviceSighting)
            .where(models.DeviceSighting.run_id == run_id)
        )
        or 0
    )
    rows = await session.execute(
        base.order_by(models.DeviceSighting.seen_at.desc(), models.DeviceSighting.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return schemas.DiscoveryObservationPageOut(
        total=total,
        items=[
            schemas.DiscoveryObservationOut(
                id=sighting.id,
                device_id=device.id,
                mac_address=device.mac_address,
                label=device.label,
                vendor=device.vendor,
                type=device.type,
                ip_address=sighting.ip_address,
                source=sighting.source,
                evidence=sighting.evidence,
                seen_at=sighting.seen_at,
            )
            for sighting, device in rows
        ],
    )
