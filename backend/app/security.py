"""Admin auth: username/password -> JWT, with roles, exact verification and
login throttling.

Roles (least to greatest): viewer < operator < admin.
The single configured administrator account gets its role from settings
(``admin_role``); token role claims are checked on every request.
"""
from __future__ import annotations

import logging
import secrets
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from .config import get_settings

log = logging.getLogger("zyranet.security")

ALGORITHM = "HS256"
_password_hasher = PasswordHasher()
_bearer = HTTPBearer(auto_error=False)

ROLES: tuple[str, ...] = ("viewer", "operator", "admin")
_RANK = {role: i for i, role in enumerate(ROLES)}


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return _password_hasher.verify(hashed, password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False


def create_access_token(
    username: str, role: str | None = None, expires_minutes: int | None = None
) -> str:
    s = get_settings()
    minutes = expires_minutes if expires_minutes is not None else s.jwt_expire_minutes
    now = datetime.now(UTC)
    claims = {
        "sub": username,
        "role": role or s.admin_role,
        "iss": s.jwt_issuer,
        "aud": s.jwt_audience,
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(minutes=minutes),
    }
    return jwt.encode(claims, s.admin_jwt_secret, algorithm=ALGORITHM)


def check_login(username: str, password: str) -> bool:
    """Exact credential check.

    ``admin_password`` may be either a plaintext secret or a standard Argon2
    hash. The submitted password is always compared in full — never as a
    substring — so a stored secret can never be satisfied by embedding it
    inside a longer value.
    """
    s = get_settings()
    if not secrets.compare_digest(username.encode(), s.admin_user.encode()):
        return False
    stored = s.admin_password
    if stored.startswith("$argon2"):
        return verify_password(password, stored)
    return secrets.compare_digest(password.encode(), stored.encode())


class _LoginThrottle:
    """Sliding-window failure counter keyed by (client IP, username)."""

    def __init__(self) -> None:
        self._failures: dict[str, list[float]] = defaultdict(list)

    def _live(self, key: str, window: int) -> list[float]:
        cutoff = time.monotonic() - window
        self._failures[key] = [t for t in self._failures[key] if t > cutoff]
        return self._failures[key]

    def is_locked(self, key: str, max_attempts: int, window: int) -> bool:
        return len(self._live(key, window)) >= max_attempts

    def record_failure(self, key: str, window: int) -> None:
        self._live(key, window).append(time.monotonic())

    def reset(self, key: str) -> None:
        self._failures.pop(key, None)

    def clear(self) -> None:
        self._failures.clear()


login_throttle = _LoginThrottle()


def client_ip(request: Request) -> str:
    s = get_settings()
    if s.trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def throttle_key(request: Request, username: str) -> str:
    return f"{client_ip(request)}|{username}"


@dataclass(frozen=True)
class Principal:
    """The authenticated caller."""

    username: str
    role: str

    def has(self, min_role: str) -> bool:
        if min_role not in _RANK:
            raise ValueError(f"unknown role: {min_role}")
        return _RANK.get(self.role, -1) >= _RANK[min_role]


def _decode(token: str) -> Principal:
    s = get_settings()
    payload = jwt.decode(
        token,
        s.admin_jwt_secret,
        algorithms=[ALGORITHM],
        audience=s.jwt_audience,
        issuer=s.jwt_issuer,
    )
    sub = str(payload.get("sub", ""))
    role = str(payload.get("role", "viewer"))
    if not sub:
        raise JWTError("missing subject")
    return Principal(username=sub, role=role if role in _RANK else "viewer")


async def get_principal(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> Principal:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing credentials")
    try:
        return _decode(creds.credentials)
    except JWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token") from exc


def require_role(min_role: str) -> Callable[..., Principal]:
    """Dependency factory: ``Depends(require_role("operator"))``."""

    async def dependency(principal: Principal = Depends(get_principal)) -> Principal:
        if not principal.has(min_role):
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"requires {min_role} role")
        return principal

    return dependency


async def require_admin(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    """Legacy guard used by the existing /api routers (returns the username)."""
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing credentials")
    try:
        principal = _decode(creds.credentials)
    except JWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token") from exc
    if not principal.has("admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "requires admin role")
    return principal.username
