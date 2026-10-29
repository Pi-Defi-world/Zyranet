"""Device inventory + live network discovery endpoints (admin)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .. import models
from ..config import get_settings
from ..db import get_session
from ..security import require_admin
from ..services import scanner

router = APIRouter(prefix="/devices", tags=["devices"], dependencies=[Depends(require_admin)])


@router.get("")
async def list_devices(
    online: bool | None = None,
    q: str | None = Query(None, description="filter by MAC/IP/hostname/vendor"),
    limit: int = 200,
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
):
    stmt = select(models.Device).order_by(models.Device.last_seen.desc())
    if online is not None:
        stmt = stmt.where(models.Device.online == online)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            (models.Device.mac_address.ilike(like))
            | (models.Device.ip_address.ilike(like))
            | (models.Device.hostname.ilike(like))
            | (models.Device.vendor.ilike(like))
        )
    stmt = stmt.offset(offset).limit(limit)
    rows = await session.scalars(stmt)
    total = await session.scalar(select(func.count()).select_from(models.Device))
    return {
        "total": int(total or 0),
        "devices": [
            {
                "id": d.id,
                "mac": d.mac_address,
                "ip": d.ip_address,
                "hostname": d.hostname,
                "vendor": d.vendor,
                "type": d.type,
                "ap": d.source_ap,
                "online": d.online,
                "first_seen": d.first_seen,
                "last_seen": d.last_seen,
            }
            for d in rows
        ],
    }


@router.get("/sessions")
async def list_sessions(
    limit: int = 100,
    session: AsyncSession = Depends(get_session),
):
    """Live RADIUS sessions (from radacct) — who is connected right now."""
    rows = await session.scalars(
        select(models.RadAcct)
        .where(models.RadAcct.acctstoptime.is_(None))
        .order_by(models.RadAcct.acctstarttime.desc())
        .limit(limit)
    )
    return [
        {
            "user": r.username,
            "nas": r.nasipaddress,
            "ip": r.framedipaddress,
            "mac": r.calledstationid,
            "start": r.acctstarttime,
            "session_time": r.acctsessiontime,
        }
        for r in rows
    ]


@router.post("/scan")
async def trigger_scan(session: AsyncSession = Depends(get_session)):
    s = get_settings()
    result = await scanner.scan(session, s.scan_cidr_list)
    return result


@router.get("/{mac}")
async def get_device(mac: str, session: AsyncSession = Depends(get_session)):
    device = await session.scalar(
        select(models.Device)
        .where(models.Device.mac_address == mac.lower())
        .options(selectinload(models.Device.sightings))
    )
    if device is None:
        raise HTTPException(404, "device not found")
    return {
        "id": device.id,
        "mac": device.mac_address,
        "ip": device.ip_address,
        "hostname": device.hostname,
        "vendor": device.vendor,
        "type": device.type,
        "ap": device.source_ap,
        "online": device.online,
        "first_seen": device.first_seen,
        "last_seen": device.last_seen,
        "sightings": [
            {"ip": s.ip_address, "ap": s.source_ap, "online": s.online, "seen_at": s.seen_at}
            for s in device.sightings
        ],
    }
