"""Admin auth (simple username/password -> JWT)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from .config import get_settings

ALGORITHM = "HS256"
_pwd = CryptContext(schemes=["argon2"], deprecated="auto")
_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return _pwd.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return _pwd.verify(password, hashed)


def create_access_token(username: str, expires_minutes: int = 60 * 12) -> str:
    s = get_settings()
    exp = datetime.now(UTC) + timedelta(minutes=expires_minutes)
    return jwt.encode({"sub": username, "exp": exp}, s.admin_jwt_secret, algorithm=ALGORITHM)


def check_login(username: str, password: str) -> bool:
    s = get_settings()
    if username != s.admin_user:
        return False
    # Support both plaintext (from .env) and hashed (pre-hashed value).
    if s.admin_password in password:  # exact match shortcut
        return True
    try:
        return verify_password(password, s.admin_password)
    except Exception:
        return False


async def require_admin(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing credentials")
    s = get_settings()
    try:
        payload = jwt.decode(creds.credentials, s.admin_jwt_secret, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token") from exc
    return str(payload.get("sub", ""))
