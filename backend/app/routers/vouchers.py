"""Voucher purchase + redeem endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .. import models, schemas
from ..db import get_session
from ..services import vouchers as vsvc

router = APIRouter(tags=["vouchers"])


@router.get("/vouchers/plans", response_model=list[schemas.PlanOut])
async def list_plans(session: AsyncSession = Depends(get_session)) -> list[models.Plan]:
    rows = await session.scalars(select(models.Plan).where(models.Plan.active.is_(True)))
    return list(rows.all())


@router.post("/vouchers/purchase", response_model=schemas.PurchaseHandle)
async def purchase(payload: schemas.PurchaseRequest, session: AsyncSession = Depends(get_session)):
    txn = await vsvc.create_purchase(session, payload, user_id=None)
    return schemas.PurchaseHandle(
        id=txn.id, provider=txn.provider, provider_ref=txn.provider_ref, status=txn.status
    )


@router.post("/vouchers/redeem", response_model=schemas.RedeemResult)
async def redeem(payload: schemas.ActivateRequest, session: AsyncSession = Depends(get_session)):
    return await vsvc.redeem(session, payload.code, payload.mac_address)


@router.get("/vouchers/{code}", response_model=schemas.VoucherOut)
async def get_voucher(code: str, session: AsyncSession = Depends(get_session)):
    voucher = await session.scalar(
        select(models.Voucher)
        .where(models.Voucher.code == code)
        .options(selectinload(models.Voucher.plan))
    )
    if voucher is None:
        raise HTTPException(404, "voucher not found")
    return schemas.VoucherOut(
        code=voucher.code,
        plan_name=voucher.plan.name,
        status=voucher.status,
        valid_from=voucher.valid_from,
        valid_until=voucher.valid_until,
    )
