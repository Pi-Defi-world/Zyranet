"""Admin dashboard API (one of the two admin UIs). Requires admin JWT."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .. import models
from ..db import get_session
from ..security import require_admin

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/overview")
async def overview(session: AsyncSession = Depends(get_session)):
    active = await session.scalar(
        select(func.count()).select_from(models.Voucher).where(models.Voucher.status == "active")
    )
    unused = await session.scalar(
        select(func.count()).select_from(models.Voucher).where(models.Voucher.status == "unused")
    )
    paid_today = await session.scalar(
        select(func.count())
        .select_from(models.Transaction)
        .where(models.Transaction.status == "paid")
    )
    revenue_kobo = await session.scalar(
        select(func.sum(models.Transaction.amount_kobo)).where(models.Transaction.status == "paid")
    )
    return {
        "active_vouchers": active,
        "unused_vouchers": unused,
        "paid_transactions": paid_today,
        "revenue_kobo": int(revenue_kobo or 0),
    }


@router.get("/vouchers")
async def list_vouchers(
    limit: int = 50, offset: int = 0, session: AsyncSession = Depends(get_session)
):
    rows = await session.scalars(
        select(models.Voucher)
        .options(selectinload(models.Voucher.plan))
        .order_by(models.Voucher.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return [
        {
            "id": v.id,
            "code": v.code,
            "plan": v.plan.name,
            "status": v.status.value,
            "valid_until": v.valid_until,
            "created_at": v.created_at,
        }
        for v in rows
    ]
