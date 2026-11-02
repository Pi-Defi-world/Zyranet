"""v1 authentication endpoints — same handlers as the legacy /api/auth routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ... import schemas, security
from ..auth import login as _login

router = APIRouter(prefix="/auth", tags=["auth"])

router.post("/login", response_model=schemas.TokenOut)(_login)


@router.get("/me", response_model=schemas.CurrentUserOut)
async def me(principal: security.Principal = Depends(security.get_principal)):
    return schemas.CurrentUserOut(username=principal.username, role=principal.role)
