"""Append-only audit trail for administrative actions."""
from __future__ import annotations

from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models


async def record_audit(
    session: AsyncSession,
    *,
    actor: str,
    action: str,
    role: str | None = None,
    entity_type: str | None = None,
    entity_id: int | str | None = None,
    outcome: str = "success",
    detail: dict[str, Any] | None = None,
    request_id: str | None = None,
    commit: bool = False,
) -> models.AuditEvent:
    """Append one audit event.

    Audit rows are never updated or deleted by the application; only inserts
    happen here (``append-only`` in the application sense).
    """
    event = models.AuditEvent(
        actor=actor,
        role=role,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        outcome=outcome,
        request_id=request_id,
        detail=detail or {},
    )
    session.add(event)
    if commit:
        await session.commit()
    else:
        await session.flush()
    return event


async def record_request_audit(
    session: AsyncSession,
    request: Request,
    *,
    actor: str,
    role: str | None,
    action: str,
    entity_type: str | None = None,
    entity_id: int | str | None = None,
    outcome: str = "success",
    detail: dict[str, Any] | None = None,
    commit: bool = False,
) -> models.AuditEvent:
    """``record_audit`` that picks the request ID off the ASGI request state."""
    return await record_audit(
        session,
        actor=actor,
        role=role,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        outcome=outcome,
        detail=detail,
        request_id=getattr(request.state, "request_id", None),
        commit=commit,
    )
