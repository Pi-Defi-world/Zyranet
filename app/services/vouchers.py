"""Voucher purchase + redemption orchestration."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .. import models, schemas
from ..enums import TxnStatus, VoucherStatus
from . import codegen, radius


async def create_purchase(
    session: AsyncSession, payload: schemas.PurchaseRequest, user_id: int | None
) -> models.Transaction:
    plan = await session.scalar(
        select(models.Plan).where(
            models.Plan.name == payload.plan_name, models.Plan.active.is_(True)
        )
    )
    if plan is None:
        raise ValueError(f"Unknown/inactive plan: {payload.plan_name}")

    voucher = models.Voucher(code=codegen.make_voucher_code(), plan_id=plan.id, user_id=user_id)
    session.add(voucher)
    await session.flush()

    txn = models.Transaction(
        voucher_id=voucher.id,
        user_id=user_id,
        provider=payload.provider,
        provider_ref=f"ZR-{uuid4().hex[:12].upper()}",
        amount_kobo=plan.price_kobo,
        currency=plan.price_currency,
        status=TxnStatus.pending,
    )
    session.add(txn)
    await session.commit()
    return txn


async def activate_on_success(session: AsyncSession, voucher_id: int) -> models.Voucher:
    """Mark a voucher active + push it into the RADIUS tables. Idempotent."""
    voucher = await session.scalar(
        select(models.Voucher)
        .where(models.Voucher.id == voucher_id)
        .options(selectinload(models.Voucher.plan))
    )
    if voucher is None:
        raise ValueError("voucher not found")
    if voucher.status == VoucherStatus.active:
        return voucher

    now = datetime.now(UTC)
    voucher.valid_from = now
    voucher.valid_until = now + timedelta(seconds=voucher.plan.duration_seconds)
    voucher.status = VoucherStatus.active
    voucher.used_at = now
    await session.flush()

    await radius.activate_voucher(session, voucher)
    await session.commit()
    return voucher


def _aware(dt: datetime | None) -> datetime | None:
    """Make a datetime UTC-aware if it happens to be naive (e.g. from SQLite)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


async def redeem(session: AsyncSession, code: str, mac_address: str) -> schemas.RedeemResult:
    """Called by the portal flow: bind MAC, enforce single-use + time window."""
    voucher = await session.scalar(select(models.Voucher).where(models.Voucher.code == code))
    if voucher is None:
        return schemas.RedeemResult(accepted=False, reason="invalid_code")

    if voucher.status == VoucherStatus.revoked:
        return schemas.RedeemResult(accepted=False, reason="revoked")
    if voucher.status == VoucherStatus.expired:
        return schemas.RedeemResult(accepted=False, reason="expired")

    now = datetime.now(UTC)
    valid_from = _aware(voucher.valid_from)
    valid_until = _aware(voucher.valid_until)
    if valid_from is None or valid_until is None:
        return schemas.RedeemResult(accepted=False, reason="not_active")
    if now > valid_until:
        voucher.status = VoucherStatus.expired
        await radius.deactivate_voucher(session, voucher.code)
        await session.commit()
        return schemas.RedeemResult(accepted=False, reason="expired")
    if now < valid_from:
        return schemas.RedeemResult(accepted=False, reason="not_yet_valid")

    # Enforce single-use: already bound to a different MAC?
    bound = await session.scalar(
        select(models.RedeemedDevice).where(models.RedeemedDevice.voucher_id == voucher.id)
    )
    if bound is not None and bound.mac_address.lower() != mac_address.lower():
        return schemas.RedeemResult(accepted=False, reason="already_in_use")

    if bound is None:
        session.add(models.RedeemedDevice(voucher_id=voucher.id, mac_address=mac_address))
    else:
        bound.last_seen = now

    remaining = int((valid_until - now).total_seconds())
    await session.commit()
    return schemas.RedeemResult(accepted=True, remaining_seconds=remaining)
