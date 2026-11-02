"""SPA static serving: React dashboard at /, API routes remain isolated."""
from __future__ import annotations

import pytest

import app.main as mainmod


@pytest.fixture
def spa_dir(tmp_path, monkeypatch):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<div id='root'>Zyranet SPA</div>", encoding="utf-8")
    (tmp_path / "assets" / "app.js").write_text("console.log('spa')", encoding="utf-8")
    monkeypatch.setattr(mainmod, "_SPA_DIR", tmp_path)
    return tmp_path


async def test_root_and_client_route_serve_index(client, spa_dir):
    root = await client.get("/")
    assert root.status_code == 200
    assert "Zyranet SPA" in root.text

    # Client-side route (React Router) falls back to index.html.
    deep = await client.get("/devices/42")
    assert deep.status_code == 200
    assert "Zyranet SPA" in deep.text


async def test_built_assets_served(client, spa_dir):
    resp = await client.get("/assets/app.js")
    assert resp.status_code == 200
    assert "console.log" in resp.text

    missing = await client.get("/assets/nope.js")
    assert missing.status_code == 404


async def test_api_paths_never_get_spa(client, spa_dir):
    unknown = await client.get("/api/v1/does-not-exist")
    assert unknown.status_code == 404
    assert "Zyranet SPA" not in unknown.text

    api = await client.get("/api/v1/auth/me")
    assert api.status_code == 401  # JSON auth error, not HTML


async def test_health_and_admin_alias_serve_spa(client, spa_dir):
    health = await client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}

    admin = await client.get("/admin", follow_redirects=False)
    assert admin.status_code == 307
    assert admin.headers["location"] == "/"


async def test_path_traversal_is_blocked(client, spa_dir):
    resp = await client.get("/../pyproject.toml")
    # Normalised by the client/ASGI layer; either way must not leak backend files.
    assert resp.status_code in (404, 400)
    assert "pythonpath" not in resp.text


async def test_root_reports_missing_frontend_without_spa(client, monkeypatch, tmp_path):
    monkeypatch.setattr(mainmod, "_SPA_DIR", tmp_path / "missing")
    resp = await client.get("/")
    assert resp.status_code == 503
