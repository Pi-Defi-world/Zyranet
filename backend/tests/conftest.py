"""Shared test fixtures: in-memory SQLite + ASGI client + admin login.

Environment defaults are pinned here so tests behave the same even when a
developer has a local .env file (pydantic-settings gives environment
variables precedence over .env).
"""
from __future__ import annotations

import os

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

os.environ.setdefault("ADMIN_USER", "admin")
os.environ.setdefault("ADMIN_PASSWORD", "change-me")
# Tests must never rewrite the committed topology seed file.
os.environ.setdefault("TOPOLOGY_AUTO_EXPORT", "false")

from app import security  # noqa: E402
from app.db import Base, get_session  # noqa: E402
from app.main import app  # noqa: E402

engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    poolclass=StaticPool,
    connect_args={"check_same_thread": False},
)
TestSession = async_sessionmaker(engine, expire_on_commit=False)


async def _override():
    async with TestSession() as session:
        yield session


@pytest_asyncio.fixture
async def db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    security.login_throttle.clear()
    yield
    security.login_throttle.clear()


@pytest_asyncio.fixture
async def session(db):
    async with TestSession() as s:
        yield s


@pytest_asyncio.fixture
async def client(db):
    app.dependency_overrides[get_session] = _override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_headers(client):
    resp = await client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "change-me"}
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}
