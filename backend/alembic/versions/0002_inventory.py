"""inventory â€” locations, device models/capabilities, interfaces, addresses,
audit events, plus inventory columns on devices.

See docs/technical_docs1.md Â§19.4 (implementation order 1-2) and
docs/Zyranet-Architecture2.md Â§12.

Revision ID: 0002_inventory
Revises: 0001_baseline
Create Date: 2026-10-30
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0002_inventory"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None

NEW_TABLES = (
    "locations",
    "device_models",
    "device_capabilities",
    "device_interfaces",
    "device_addresses",
    "audit_events",
)

DEVICE_COLUMNS = (
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
)


def upgrade() -> None:
    op.create_table(
        "locations",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("parent_id", sa.BigInteger(), sa.ForeignKey("locations.id"), nullable=True),
        sa.Column("kind", sa.String(), nullable=False, server_default="building"),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("code", sa.String(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_locations_kind", "locations", ["kind"])

    op.create_table(
        "device_models",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("vendor", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("hardware_revision", sa.String(), nullable=False, server_default=""),
        sa.Column("family", sa.String(), nullable=True),
        sa.Column("management_protocols", sa.String(), nullable=True),
        sa.Column("support_status", sa.String(), nullable=False, server_default="unknown"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("vendor", "model", "hardware_revision", name="uq_model_revision"),
    )

    op.create_table(
        "device_capabilities",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("model_id", sa.BigInteger(), sa.ForeignKey("device_models.id"), nullable=False),
        sa.Column("capability", sa.String(), nullable=False),
        sa.Column("support_level", sa.String(), nullable=False, server_default="read"),
        sa.Column("adapter", sa.String(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.UniqueConstraint("model_id", "capability", name="uq_model_capability"),
    )

    op.create_table(
        "device_interfaces",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("device_id", sa.BigInteger(), sa.ForeignKey("devices.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False, server_default="ethernet"),
        sa.Column("mac_address", sa.String(), nullable=True),
        sa.Column("link_state", sa.String(), nullable=True),
        sa.Column("speed_mbps", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("device_id", "name", name="uq_device_interface"),
    )

    op.create_table(
        "device_addresses",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("device_id", sa.BigInteger(), sa.ForeignKey("devices.id"), nullable=False),
        sa.Column("address", sa.String(), nullable=False),
        sa.Column("prefix_length", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(), nullable=False, server_default="observed"),
        sa.Column("current", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "first_seen",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "last_seen",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_device_addresses_address", "device_addresses", ["address"])

    op.create_table(
        "audit_events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("actor", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("entity_type", sa.String(), nullable=True),
        sa.Column("entity_id", sa.String(), nullable=True),
        sa.Column("outcome", sa.String(), nullable=False, server_default="success"),
        sa.Column("request_id", sa.String(), nullable=True),
        sa.Column("detail", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_audit_created_at", "audit_events", ["created_at"])
    op.create_index("idx_audit_actor", "audit_events", ["actor"])
    op.create_index("idx_audit_action", "audit_events", ["action"])

    # --- inventory columns on the existing devices table ---
    op.add_column("devices", sa.Column("label", sa.String(), nullable=True))
    op.add_column(
        "devices",
        sa.Column("model_id", sa.BigInteger(), sa.ForeignKey("device_models.id"), nullable=True),
    )
    op.add_column(
        "devices",
        sa.Column("location_id", sa.BigInteger(), sa.ForeignKey("locations.id"), nullable=True),
    )
    op.add_column("devices", sa.Column("serial_number", sa.String(), nullable=True))
    op.add_column("devices", sa.Column("hardware_revision", sa.String(), nullable=True))
    op.add_column("devices", sa.Column("firmware", sa.String(), nullable=True))
    op.add_column("devices", sa.Column("role", sa.String(), nullable=True))
    op.add_column(
        "devices",
        sa.Column(
            "condition", sa.String(), nullable=False, server_default="unverified"
        ),
    )
    op.add_column(
        "devices",
        sa.Column(
            "identity_confidence", sa.String(), nullable=False, server_default="unknown"
        ),
    )
    op.add_column("devices", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column(
        "devices",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    for column in DEVICE_COLUMNS:
        op.drop_column("devices", column)
    for table in reversed(NEW_TABLES):
        op.drop_table(table)
