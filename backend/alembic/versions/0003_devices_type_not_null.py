"""devices.type must be NOT NULL (the ORM always writes a value and
db/schema.sql supplies DEFAULT 'unknown', but the column was created without
NOT NULL).

Revision ID: 0003_devices_type_not_null
Revises: 0002_inventory
Create Date: 2026-10-30
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0003_devices_type_not_null"
down_revision = "0002_inventory"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("UPDATE devices SET type = 'unknown' WHERE type IS NULL"))
    op.alter_column("devices", "type", existing_type=sa.Text(), nullable=False)


def downgrade() -> None:
    op.alter_column("devices", "type", existing_type=sa.Text(), nullable=True)
