"""End-to-end smoke test using an in-memory SQLite store and an ASGI client.

Proves the FastAPI app boots, routes resolve, and the voucher purchase ->
activation -> RADIUS-sync path works without a real Postgres/RADIUS.
"""
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
from app.services.payments import paystack as paystack_mod
from app.services.payments.base import PaymentStatus

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
async def client(tmp_path):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    app.dependency_overrides[get_session] = _override

    async with TestSession() as s:
        s.add(
            models.Plan(
                name="15h", duration_seconds=54000, price_kobo=20000, price_currency="NGN"
            )
        )
        await s.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_list_plans(client):
    resp = await client.get("/api/vouchers/plans")
    assert resp.status_code == 200
    data = resp.json()
    assert any(p["name"] == "15h" for p in data)


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


@pytest.mark.asyncio
async def test_purchase_and_redeem(client, monkeypatch):
    # Stub the provider verify so we don't hit the real Paystack API.
    async def fake_verify(self, provider_ref):
        return PaymentStatus(paid=True, provider_ref=provider_ref, amount_kobo=20000)

    monkeypatch.setattr(paystack_mod.PaystackProvider, "verify", fake_verify)
    # Purchase (creates pending transaction + unused voucher).
    resp = await client.post(
        "/api/vouchers/purchase",
        json={"plan_name": "15h", "provider": "paystack"},
    )
    assert resp.status_code == 200
    tx = resp.json()
    assert tx["status"] == "pending"

    # Simulate a payment webhook confirming success.
    ref = tx["provider_ref"]
    resp = await client.post(
        "/api/payments/paystack/webhook",
        json={"data": {"reference": ref}},
    )
    assert resp.status_code == 200

    # Voucher now active, per-user 15h, single-use: redeem a MAC.
    resp = await client.post(
        "/api/vouchers/redeem",
        json={"code": "UNKNOWN", "mac_address": "00:11:22:33:44:55"},
    )
    assert resp.json()["accepted"] is False

    # Grab the active voucher code from the DB to redeem.
    async with TestSession() as s:
        v = await s.scalar(select(models.Voucher))
        code = v.code

    resp = await client.post(
        "/api/vouchers/redeem",
        json={"code": code, "mac_address": "00:11:22:33:44:55"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["accepted"] is True
    assert 0 < body["remaining_seconds"] <= 54000

    # Same voucher on a second device -> denied (single-use).
    resp = await client.post(
        "/api/vouchers/redeem",
        json={"code": code, "mac_address": "A1:B2:C3:D4:E5:F6"},
    )
    assert resp.json()["accepted"] is False
    assert resp.json()["reason"] == "already_in_use"
