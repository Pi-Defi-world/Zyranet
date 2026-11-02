"""Alembic environment: async engine, URL from app settings.

FreeRADIUS tables (rad*) are excluded from autogenerate comparison because the
ORM only mirrors a subset of their columns (the SQL schema is authoritative
for those).
"""
from __future__ import annotations

import asyncio

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from app import models  # noqa: F401  (registers all tables on Base.metadata)
from app.config import get_settings
from app.db import Base

config = context.config
target_metadata = Base.metadata

# Historical payment-era records are intentionally retained in deployed
# databases until their dependencies and retention requirements are reviewed.
LEGACY_PAYMENT_TABLES = {
    "plans",
    "users",
    "vouchers",
    "transactions",
    "redeemed_devices",
    "otp_codes",
}


def _database_url() -> str:
    return get_settings().sqlalchemy_database_uri


def include_object(object, name, type_, reflected, compare_to):  # noqa: A002
    if type_ == "table" and name.startswith("rad"):
        return False
    if type_ == "table" and name in LEGACY_PAYMENT_TABLES:
        return False
    return True


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        include_object=include_object,
        compare_type=True,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
        compare_type=True,
        render_as_batch=connection.dialect.name == "sqlite",
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _database_url()
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
