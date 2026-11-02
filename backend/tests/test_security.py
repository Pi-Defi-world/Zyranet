"""Authentication, token and authorization tests (R0 security gate)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from jose import jwt
from pydantic import ValidationError

from app import security
from app.config import Settings, get_settings


@pytest.fixture
def settings_override(monkeypatch):
    """Replace configured credentials/limits for one test, then restore."""

    def apply(**env):
        for key, value in env.items():
            monkeypatch.setenv(key, str(value))
        get_settings.cache_clear()
        security.login_throttle.clear()

    yield apply
    get_settings.cache_clear()
    security.login_throttle.clear()


def test_production_settings_reject_placeholder_secrets():
    with pytest.raises(ValidationError, match="invalid production configuration"):
        Settings(_env_file=None, app_env="production")


def test_production_settings_accept_explicit_secrets_and_https_hosts():
    settings = Settings(
        _env_file=None,
        app_env="production",
        db_password="a-unique-database-secret-with-32-bytes",
        admin_jwt_secret="a-unique-jwt-signing-secret-with-at-least-32-characters",
        admin_password="a-unique-admin-password-with-length",
        allowed_hosts="zyranet.example.edu,localhost,127.0.0.1",
        cors_allowed_origins="https://zyranet.example.edu",
    )

    assert settings.app_env == "production"


def test_database_url_escapes_password_special_characters():
    settings = Settings(
        _env_file=None,
        db_password="p@ss:word/with?symbols",
    )

    assert settings.sqlalchemy_database_uri.endswith(
        "@localhost:5432/zyranet"
    )
    assert "p%40ss%3Aword%2Fwith%3Fsymbols" in settings.sqlalchemy_database_uri


async def test_login_success_and_me(client):
    resp = await client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "change-me"}
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]

    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json() == {"username": "admin", "role": "admin"}


async def test_login_rejects_wrong_password(client):
    resp = await client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "wrong"}
    )
    assert resp.status_code == 401


async def test_password_must_match_exactly_not_as_substring(client, settings_override):
    """Regression: the old check_login accepted any password *containing* the
    configured secret (``stored in submitted``). It must be exact."""
    settings_override(ADMIN_PASSWORD="school-secret")

    ok = await client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "school-secret"}
    )
    assert ok.status_code == 200

    embedded = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "school-secret-plus-extra"},
    )
    assert embedded.status_code == 401

    wrapped = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "xx-school-secretxx"},
    )
    assert wrapped.status_code == 401


async def test_hashed_admin_password_is_supported(client, settings_override):
    settings_override(ADMIN_PASSWORD=security.hash_password("s3cret-hash"))

    resp = await client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "s3cret-hash"}
    )
    assert resp.status_code == 200

    bad = await client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "wrong"}
    )
    assert bad.status_code == 401


async def test_login_throttled_after_max_attempts(client, settings_override):
    settings_override(LOGIN_MAX_ATTEMPTS=3, LOGIN_LOCKOUT_SECONDS=300)

    for _ in range(3):
        resp = await client.post(
            "/api/v1/auth/login", json={"username": "admin", "password": "nope"}
        )
        assert resp.status_code == 401

    locked = await client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "change-me"}
    )
    assert locked.status_code == 429


async def test_unknown_username_is_also_throttled(client, settings_override):
    settings_override(LOGIN_MAX_ATTEMPTS=2, LOGIN_LOCKOUT_SECONDS=300)

    for _ in range(2):
        resp = await client.post(
            "/api/v1/auth/login", json={"username": "nobody", "password": "x"}
        )
        assert resp.status_code == 401

    resp = await client.post(
        "/api/v1/auth/login", json={"username": "nobody", "password": "x"}
    )
    assert resp.status_code == 429


async def test_endpoints_require_token(client, auth_headers):
    for path in ("/api/v1/devices", "/api/v1/locations", "/api/v1/device-models",
                 "/api/v1/audit-events"):
        resp = await client.get(path)
        assert resp.status_code == 401, path

    ok = await client.get("/api/v1/devices", headers=auth_headers)
    assert ok.status_code == 200


async def test_tampered_token_rejected(client, auth_headers):
    token = auth_headers["Authorization"].removeprefix("Bearer ")
    s = get_settings()
    payload = jwt.decode(token, s.admin_jwt_secret, audience=s.jwt_audience,
                         issuer=s.jwt_issuer)
    payload["sub"] = "intruder"
    forged = jwt.encode(payload, "wrong-secret", algorithm="HS256")

    resp = await client.get("/api/v1/devices", headers={"Authorization": f"Bearer {forged}"})
    assert resp.status_code == 401


async def test_wrong_audience_token_rejected(client):
    s = get_settings()
    now = datetime.now(UTC)
    claims = {
        "sub": "admin",
        "role": "admin",
        "iss": s.jwt_issuer,
        "aud": "someone-else",
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(minutes=5),
    }
    token = jwt.encode(claims, s.admin_jwt_secret, algorithm="HS256")
    resp = await client.get("/api/v1/devices", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


async def test_role_enforcement_on_writes(client, auth_headers):
    viewer_token = security.create_access_token("viewer-user", role="viewer")
    viewer = {"Authorization": f"Bearer {viewer_token}"}

    read = await client.get("/api/v1/devices", headers=viewer)
    assert read.status_code == 200

    write = await client.post(
        "/api/v1/locations",
        json={"kind": "building", "name": "Library"},
        headers=viewer,
    )
    assert write.status_code == 403


async def test_legacy_admin_routes_work_with_admin_token(client, auth_headers):
    resp = await client.get("/api/devices", headers=auth_headers)
    assert resp.status_code == 200
