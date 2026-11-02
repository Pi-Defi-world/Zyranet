"""Add an operator-triggered discovery queue and single active-run guard.

Revision ID: 0005_discovery_queue
Revises: 0004_discovery_runs
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0005_discovery_queue"
down_revision = "0004_discovery_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "discovery_runs",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("discovery_runs", sa.Column("requested_by", sa.String(), nullable=True))
    op.execute("UPDATE discovery_runs SET created_at = started_at WHERE created_at IS NULL")
    # Close legacy in-flight rows before enforcing one active run globally.
    op.execute(
        "UPDATE discovery_runs SET status = 'failed', "
        "error = 'closed during discovery queue migration', "
        "completed_at = CURRENT_TIMESTAMP WHERE status = 'running'"
    )
    with op.batch_alter_table("discovery_runs") as batch:
        batch.alter_column("created_at", nullable=False, server_default=sa.func.now())
        batch.alter_column("started_at", nullable=True)

    op.create_index(
        "uq_discovery_one_active_run",
        "discovery_runs",
        [sa.text("(1)")],
        unique=True,
        postgresql_where=sa.text("status IN ('queued', 'running')"),
        sqlite_where=sa.text("status IN ('queued', 'running')"),
    )


def downgrade() -> None:
    op.drop_index("uq_discovery_one_active_run", table_name="discovery_runs")
    op.execute(
        "UPDATE discovery_runs SET status = 'failed', "
        "error = 'queued run closed during queue migration rollback', "
        "completed_at = CURRENT_TIMESTAMP, started_at = created_at WHERE status = 'queued'"
    )
    with op.batch_alter_table("discovery_runs") as batch:
        batch.alter_column("started_at", nullable=False)
        batch.drop_column("requested_by")
        batch.drop_column("created_at")
