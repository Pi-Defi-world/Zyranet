"""baseline — executes db/schema.sql (network inventory + FreeRADIUS tables).

The script is split into individual statements and re-run safely: CREATE TYPE
is wrapped in a DO block so an already-initialized database (loaded from
schema.sql before Alembic was adopted) can simply run `alembic upgrade head`.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-10-30
"""
from __future__ import annotations

from pathlib import Path

import sqlalchemy as sa

from alembic import op

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "db" / "schema.sql"

BASELINE_TABLES = (
    "radcheck",
    "radreply",
    "radgroupcheck",
    "radgroupreply",
    "radusergroup",
    "radacct",
    "radpostauth",
    "devices",
    "device_sightings",
    "topology_document",
)


def _statements() -> list[str]:
    """Read schema.sql and return executable statements."""
    lines = []
    for line in SCHEMA_PATH.read_text(encoding="utf-8").splitlines():
        lines.append(line.split("--", 1)[0])
    text = "\n".join(lines)

    statements: list[str] = []
    for raw in text.split(";"):
        stmt = " ".join(raw.split())
        if not stmt or stmt.upper() in {"BEGIN", "COMMIT", "END"}:
            continue
        if stmt.upper().startswith("CREATE TYPE "):
            # CREATE TYPE has no IF NOT EXISTS; guard it so the baseline is
            # idempotent for databases initialized before Alembic was adopted.
            stmt = f"DO $$ BEGIN {stmt}; EXCEPTION WHEN duplicate_object THEN NULL; END $$"
        statements.append(stmt)
    return statements


def upgrade() -> None:
    for statement in _statements():
        op.execute(sa.text(statement))


def downgrade() -> None:
    # Do not drop legacy payment-era tables. Existing deployments may contain
    # records whose retention and dependencies have not yet been reviewed.
    for table in reversed(BASELINE_TABLES):
        op.execute(sa.text(f"DROP TABLE IF EXISTS {table} CASCADE"))
