"""Smoke tests using an in-memory SQLite store and an ASGI client."""
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app import models
from app.db import Base, get_session
from app.main import app

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
async def client():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    app.dependency_overrides[get_session] = _override

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_devices_upsert(client):
    from app.services.scanner import SeenDevice, _upsert

    async with TestSession() as s:
        await _upsert(s, SeenDevice(mac="AA:BB:CC:DD:EE:FF", ip="10.10.20.99", online=True))
        await s.commit()

    async with TestSession() as s:
        d = await s.scalar(
            select(models.Device).where(models.Device.mac_address == "aa:bb:cc:dd:ee:ff")
        )
        assert d is not None
        assert d.ip_address == "10.10.20.99"
        assert d.online is True
        sightings = await s.scalar(
            select(func.count()).select_from(models.DeviceSighting).where(
                models.DeviceSighting.device_id == d.id
            )
        )
        assert sightings >= 1
