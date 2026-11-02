"""Admin authentication endpoints (legacy /api prefix)."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from .. import schemas, security
from ..config import get_settings
from ..db import get_session
from ..services.audit import record_audit

log = logging.getLogger("zyranet.auth")

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=schemas.TokenOut)
async def login(
    payload: schemas.LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    s = get_settings()
    key = security.throttle_key(request, payload.username)
    if security.login_throttle.is_locked(
        key, s.login_max_attempts, s.login_lockout_seconds
    ):
        raise HTTPException(429, "too many failed attempts, try again later")

    if not security.check_login(payload.username, payload.password):
        security.login_throttle.record_failure(key, s.login_lockout_seconds)
        log.warning("failed login for %r from %s", payload.username, key.split("|", 1)[0])
        raise HTTPException(401, "invalid credentials")

    security.login_throttle.reset(key)
    token = security.create_access_token(payload.username)
    try:
        await record_audit(
            session,
            actor=payload.username,
            role=s.admin_role,
            action="auth.login",
            request_id=getattr(request.state, "request_id", None),
            commit=True,
        )
    except Exception:  # pragma: no cover - auditing must not block login
        log.exception("could not record login audit event")
    return schemas.TokenOut(access_token=token)


@router.get("/me", response_model=schemas.CurrentUserOut)
async def me(principal: security.Principal = Depends(security.get_principal)):
    return schemas.CurrentUserOut(username=principal.username, role=principal.role)
