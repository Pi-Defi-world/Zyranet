"""Persist discovery sweeps and observation evidence.

Revision ID: 0004_discovery_runs
Revises: 0003_devices_type_not_null
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0004_discovery_runs"
down_revision = "0003_devices_type_not_null"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "discovery_runs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("status", sa.String(), nullable=False, server_default="running"),
        sa.Column("scope", sa.JSON(), nullable=False),
        sa.Column("targets_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("probes_responded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("probe_errors", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("devices_observed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_discovery_runs_started_at", "discovery_runs", ["started_at"])
    op.create_index("idx_discovery_runs_status", "discovery_runs", ["status"])

    op.add_column(
        "device_sightings",
        sa.Column("run_id", sa.BigInteger(), sa.ForeignKey("discovery_runs.id"), nullable=True),
    )
    op.add_column(
        "device_sightings",
        sa.Column("source", sa.String(), nullable=False, server_default="neighbor_table"),
    )
    op.add_column(
        "device_sightings",
        sa.Column("evidence", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.create_index("idx_sightings_run", "device_sightings", ["run_id"])


def downgrade() -> None:
    op.drop_index("idx_sightings_run", table_name="device_sightings")
    op.drop_column("device_sightings", "evidence")
    op.drop_column("device_sightings", "source")
    op.drop_column("device_sightings", "run_id")
    op.drop_index("idx_discovery_runs_status", table_name="discovery_runs")
    op.drop_index("idx_discovery_runs_started_at", table_name="discovery_runs")
    op.drop_table("discovery_runs")
