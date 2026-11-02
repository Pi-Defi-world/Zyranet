"""Migration tests — require a real PostgreSQL (CI sets this).

Skipped in the default dev run (SQLite) because db/schema.sql uses
PostgreSQL-specific syntax. CI provides TEST_MIGRATION_DATABASE_URL pointing
at a scratch database.
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path

import asyncpg
import pytest

BACKEND = Path(__file__).resolve().parents[1]
MIGRATION_URL = os.environ.get("TEST_MIGRATION_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not MIGRATION_URL, reason="set TEST_MIGRATION_DATABASE_URL (postgres) to run migration tests"
)

EXPECTED_TABLES = {
    "devices",
    "device_sightings",
    "topology_document",
    "locations",
    "device_models",
    "device_capabilities",
    "device_interfaces",
    "device_addresses",
    "audit_events",
    "links",
    "link_endpoints",
    "topology_observations",
}

EXPECTED_DEVICE_COLUMNS = {
    "label",
    "model_id",
    "location_id",
    "serial_number",
    "hardware_revision",
    "firmware",
    "role",
    "condition",
    "identity_confidence",
    "notes",
    "created_at",
}


def _alembic(*args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "DB_URL": MIGRATION_URL}
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"alembic {' '.join(args)} failed:\n{result.stdout}\n{result.stderr}"
    )
    return result


def _dsn() -> str:
    return MIGRATION_URL.replace("postgresql+asyncpg://", "postgres://")


async def test_upgrade_head_builds_full_schema():
    conn = await asyncpg.connect(_dsn())
    try:
        # Start from an empty schema so the test is re-runnable.
        await conn.execute("DROP SCHEMA public CASCADE")
        await conn.execute("CREATE SCHEMA public")
    finally:
        await conn.close()

    await asyncio.to_thread(_alembic, "upgrade", "head")

    conn = await asyncpg.connect(_dsn())
    try:
        tables = {
            row["tablename"]
            for row in await conn.fetch(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
            )
        }
        assert EXPECTED_TABLES <= tables, f"missing: {EXPECTED_TABLES - tables}"

        columns = {
            row["column_name"]
            for row in await conn.fetch(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'devices'"
            )
        }
        assert EXPECTED_DEVICE_COLUMNS <= columns, f"missing: {EXPECTED_DEVICE_COLUMNS - columns}"

        version = await conn.fetchval("SELECT version_num FROM alembic_version")
        assert version
    finally:
        await conn.close()

    # Running upgrade again must be a no-op (idempotent baseline + guards).
    _alembic("upgrade", "head")


async def test_models_match_migrations():
    """Autogenerate must see no drift between ORM models and migrations."""
    conn = await asyncpg.connect(_dsn())
    try:
        version = await conn.fetchval("SELECT version_num FROM alembic_version")
    finally:
        await conn.close()
    if not version:
        pytest.skip("run test_upgrade_head_builds_full_schema first")

    result = await asyncio.to_thread(
        _alembic, "revision", "--autogenerate", "-m", "drift-probe"
    )
    output = result.stdout + result.stderr
    generated = [p for p in (BACKEND / "alembic" / "versions").glob("*drift_probe*")]
    try:
        if generated:
            body = generated[0].read_text(encoding="utf-8")
            assert "pass" in body.split("def upgrade()")[1].split("def downgrade")[0], (
                f"autogenerate detected drift:\n{body}"
            )
        else:
            assert "No changes detected" in output, output
    finally:
        for path in generated:
            path.unlink()


async def test_downgrade_and_reupgrade_round_trip():
    """Exercise every downgrade against the disposable PostgreSQL database."""
    conn = await asyncpg.connect(_dsn())
    try:
        version = await conn.fetchval("SELECT version_num FROM alembic_version")
    finally:
        await conn.close()
    if not version:
        pytest.skip("run test_upgrade_head_builds_full_schema first")

    await asyncio.to_thread(_alembic, "downgrade", "base")

    conn = await asyncpg.connect(_dsn())
    try:
        assert await conn.fetchval("SELECT to_regclass('public.devices') IS NOT NULL") is False
        assert await conn.fetchval("SELECT to_regclass('public.links') IS NOT NULL") is False
    finally:
        await conn.close()

    await asyncio.to_thread(_alembic, "upgrade", "head")
    conn = await asyncpg.connect(_dsn())
    try:
        assert await conn.fetchval("SELECT to_regclass('public.devices') IS NOT NULL") is True
        assert await conn.fetchval("SELECT to_regclass('public.links') IS NOT NULL") is True
    finally:
        await conn.close()
