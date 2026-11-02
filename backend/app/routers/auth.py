"""Admin authentication endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import schemas, security

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=schemas.TokenOut)
async def login(payload: schemas.LoginRequest):
    if not security.check_login(payload.username, payload.password):
        raise HTTPException(401, "invalid credentials")
    return schemas.TokenOut(access_token=security.create_access_token(payload.username))
