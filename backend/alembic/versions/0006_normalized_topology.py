"""Add normalized, evidence-backed topology records.

Revision ID: 0006_normalized_topology
Revises: 0005_discovery_queue
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0006_normalized_topology"
down_revision = "0005_discovery_queue"
branch_labels = None
depends_on = None

PK = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "links",
        sa.Column("id", PK, primary_key=True, autoincrement=True),
        sa.Column("label", sa.String(120), nullable=True),
        sa.Column("link_type", sa.String(20), nullable=False, server_default="physical"),
        sa.Column("medium", sa.String(20), nullable=False, server_default="unknown"),
        sa.Column(
            "verification_status", sa.String(20), nullable=False, server_default="reported"
        ),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("source", sa.String(80), nullable=False, server_default="manual"),
        sa.Column("verification_evidence", sa.Text(), nullable=True),
        sa.Column("evidence", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(120), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "link_type IN ('physical', 'logical', 'wan')", name="ck_links_type"
        ),
        sa.CheckConstraint(
            "medium IN ('ethernet', 'fiber', 'wireless', 'wan', 'logical', 'other', 'unknown')",
            name="ck_links_medium",
        ),
        sa.CheckConstraint(
            "verification_status IN ('reported', 'observed', 'associated', 'verified')",
            name="ck_links_verification_status",
        ),
        sa.CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_links_confidence",
        ),
    )
    op.create_index("idx_links_status", "links", ["verification_status"])

    op.create_table(
        "link_endpoints",
        sa.Column("id", PK, primary_key=True, autoincrement=True),
        sa.Column(
            "link_id",
            sa.BigInteger(),
            sa.ForeignKey("links.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("side", sa.String(1), nullable=False),
        sa.Column("device_id", sa.BigInteger(), sa.ForeignKey("devices.id"), nullable=False),
        sa.Column(
            "interface_id",
            sa.BigInteger(),
            sa.ForeignKey("device_interfaces.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.UniqueConstraint("link_id", "side", name="uq_link_endpoint_side"),
        sa.CheckConstraint("side IN ('A', 'B')", name="ck_link_endpoint_side"),
    )
    op.create_index("idx_link_endpoints_device", "link_endpoints", ["device_id"])
    op.create_index("idx_link_endpoints_interface", "link_endpoints", ["interface_id"])

    op.create_table(
        "topology_observations",
        sa.Column("id", PK, primary_key=True, autoincrement=True),
        sa.Column(
            "device_id",
            sa.BigInteger(),
            sa.ForeignKey("devices.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "link_id",
            sa.BigInteger(),
            sa.ForeignKey("links.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "discovery_run_id",
            sa.BigInteger(),
            sa.ForeignKey("discovery_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("source", sa.String(80), nullable=False),
        sa.Column(
            "verification_status", sa.String(20), nullable=False, server_default="observed"
        ),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("evidence", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "observed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "device_id IS NOT NULL OR link_id IS NOT NULL",
            name="ck_topology_observation_target",
        ),
        sa.CheckConstraint(
            "verification_status IN ('reported', 'observed', 'associated', 'verified')",
            name="ck_topology_observation_status",
        ),
        sa.CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_topology_observation_confidence",
        ),
    )
    op.create_index("idx_topology_observations_device", "topology_observations", ["device_id"])
    op.create_index("idx_topology_observations_link", "topology_observations", ["link_id"])
    op.create_index("idx_topology_observations_run", "topology_observations", ["discovery_run_id"])
    op.create_index("idx_topology_observations_time", "topology_observations", ["observed_at"])


def downgrade() -> None:
    op.drop_index("idx_topology_observations_time", table_name="topology_observations")
    op.drop_index("idx_topology_observations_run", table_name="topology_observations")
    op.drop_index("idx_topology_observations_link", table_name="topology_observations")
    op.drop_index("idx_topology_observations_device", table_name="topology_observations")
    op.drop_table("topology_observations")
    op.drop_index("idx_link_endpoints_interface", table_name="link_endpoints")
    op.drop_index("idx_link_endpoints_device", table_name="link_endpoints")
    op.drop_table("link_endpoints")
    op.drop_index("idx_links_status", table_name="links")
    op.drop_table("links")
