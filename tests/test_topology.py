"""Topology document persistence."""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import Base, get_session
from app.main import app
from app.services import topology_store

engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    poolclass=StaticPool,
    connect_args={"check_same_thread": False},
)
TestSession = async_sessionmaker(engine, expire_on_commit=False)


async def _override():
    async with TestSession() as session:
        yield session


@pytest.mark.asyncio
async def test_topology_seed_and_positions(tmp_path, monkeypatch):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    export = tmp_path / "topo.json"
    monkeypatch.setattr(topology_store, "export_document_to_file", lambda doc, path=None: export)

    async with TestSession() as session:
        doc = await topology_store.get_document(session)
        assert doc.get("nodes")
        n = await topology_store.patch_positions(session, {"sw-core": {"x": 100, "y": 200}})
        assert n == 1
        doc2 = await topology_store.get_document(session)
        sw = next(x for x in doc2["nodes"] if x["id"] == "sw-core")
        assert sw["fixed"]["x"] == 100


@pytest.mark.asyncio
async def test_topology_api_requires_auth():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    app.dependency_overrides[get_session] = _override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/api/network/document")
        assert r.status_code == 401
    app.dependency_overrides.clear()
