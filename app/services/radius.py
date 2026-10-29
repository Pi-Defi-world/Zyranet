"""Sync a voucher code into FreeRADIUS's operational tables (radcheck/radreply).

FreeRADIUS's rlm_sql reads these tables by default, so writing here makes a
voucher usable by CoovaChilli (and any other RADIUS client) with zero
per-vendor code.
"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models


async def activate_voucher(session: AsyncSession, voucher: models.Voucher) -> None:
    """Write the voucher into radcheck/radreply so FreeRADIUS can auth it.

    Idempotent: replaces any previous rows for the same username.
    """
    username = voucher.code

    # Clear stale rows (in case the voucher was reactivated/rotated).
    await session.execute(delete(models.RadCheck).where(models.RadCheck.username == username))
    await session.execute(delete(models.RadReply).where(models.RadReply.username == username))
    await session.flush()

    # Password = the code itself, so the portal form's username+password === code.
    session.add(
        models.RadCheck(username=username, attribute="Cleartext-Password", op=":=", value=username)
    )

    remaining = _remaining_seconds(voucher)
    session.add(
        models.RadReply(
            username=username, attribute="Session-Timeout", op=":=", value=str(remaining)
        )
    )
    session.add(
        models.RadReply(
            username=username, attribute="Simultaneous-Use", op=":=", value=str(voucher.max_devices)
        )
    )
    await session.flush()


async def deactivate_voucher(session: AsyncSession, username: str) -> None:
    """Remove a voucher from RADIUS tables (expire/revoke)."""
    await session.execute(delete(models.RadCheck).where(models.RadCheck.username == username))
    await session.execute(delete(models.RadReply).where(models.RadReply.username == username))
    await session.flush()


def _remaining_seconds(voucher: models.Voucher) -> int:
    valid_until = voucher.valid_until
    if valid_until is None:
        return 0
    if valid_until.tzinfo is None:
        valid_until = valid_until.replace(tzinfo=UTC)
    now = datetime.now(UTC)
    delta = valid_until - now
    return max(0, int(delta.total_seconds()))
