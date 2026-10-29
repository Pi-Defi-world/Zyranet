"""Payment webhook + callback endpoints."""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models
from ..db import get_session
from ..services import vouchers as vsvc
from ..services.payments import get_provider
from ..services.telegram import send_voucher

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/{provider}/webhook")
async def provider_webhook(
    provider: str, request: Request, session: AsyncSession = Depends(get_session)
):
    provider_obj = get_provider(provider)
    body = await request.json()

    # Resolve reference: both providers send it differently in the raw payload.
    if provider == "paystack":
        ref = body.get("data", {}).get("reference")
    else:
        ref = body.get("data", {}).get("tx_ref")

    if not ref:
        raise HTTPException(400, "missing reference")

    status = await provider_obj.verify(ref)
    if not status.paid:
        await session.execute(
            update(models.Transaction).where(models.Transaction.provider_ref == ref).values(
                status="failed"
            )
        )
        await session.commit()
        return {"ok": True}

    txn = await session.scalar(
        select(models.Transaction).where(models.Transaction.provider_ref == ref)
    )
    if txn is None:
        raise HTTPException(404, "transaction not found")

    if txn.status == "pending":
        txn.status = "paid"
        txn.paid_at = datetime.now(UTC)
        # set provider_ref if it was created without one
        if txn.provider_ref is None:
            txn.provider_ref = ref
        await session.flush()
        voucher = await vsvc.activate_on_success(session, txn.voucher_id)

        # Deliver the code via Telegram (primary, free channel).
        if txn.user_id:
            user = await session.get(models.User, txn.user_id)
            if user and user.telegram_id:
                await send_voucher(
                    user.telegram_id,
                    voucher.code,
                    voucher.plan.name,
                    str(voucher.valid_until),
                )
        return {"ok": True}

    return {"ok": True}


@router.get("/{provider}/callback")
async def provider_callback(
    provider: str, reference: str, session: AsyncSession = Depends(get_session)
):
    """Landing page shown when the payer returns from the provider checkout."""
    return {
        "status": "handled",
        "reference": reference,
        "note": "Verification is performed by the webhook. Your voucher should be delivered.",
    }
