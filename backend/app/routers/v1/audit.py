"""v1 audit trail read endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ... import models, schemas
from ...db import get_session
from ...security import Principal, require_role

router = APIRouter(prefix="/audit-events", tags=["audit"])


@router.get("", response_model=schemas.AuditPageOut)
async def list_audit_events(
    actor: str | None = None,
    action: str | None = None,
    entity_type: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
    _: Principal = Depends(require_role("viewer")),
):
    stmt = select(models.AuditEvent).order_by(models.AuditEvent.created_at.desc())
    count_stmt = select(func.count()).select_from(models.AuditEvent)
    if actor:
        stmt = stmt.where(models.AuditEvent.actor == actor)
        count_stmt = count_stmt.where(models.AuditEvent.actor == actor)
    if action:
        # Prefix match makes grouped action families easy to query.
        prefix = f"{action}%"
        stmt = stmt.where(models.AuditEvent.action.like(prefix))
        count_stmt = count_stmt.where(models.AuditEvent.action.like(prefix))
    if entity_type:
        stmt = stmt.where(models.AuditEvent.entity_type == entity_type)
        count_stmt = count_stmt.where(models.AuditEvent.entity_type == entity_type)

    total = int(await session.scalar(count_stmt) or 0)
    rows = await session.scalars(stmt.offset(offset).limit(limit))
    return schemas.AuditPageOut(
        total=total,
        items=[schemas.AuditEventOut.model_validate(r) for r in rows],
    )
