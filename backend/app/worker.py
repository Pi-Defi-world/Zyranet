"""Scheduled network discovery worker.

Run as a single dedicated process with ``python -m app.worker``. Keeping scans
out of the API lifecycle prevents each API replica from independently sweeping
the network and lets discovery be restarted without interrupting API traffic.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update

from . import models
from .config import get_settings
from .db import async_session, engine
from .logging_config import configure_logging
from .services import scanner


async def _claim_next_run():
    """Atomically claim the oldest queued scan (PostgreSQL uses row locking)."""
    async with async_session() as session:
        run = await session.scalar(
            select(models.DiscoveryRun)
            .where(models.DiscoveryRun.status == "queued")
            .order_by(models.DiscoveryRun.created_at, models.DiscoveryRun.id)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if run is None:
            await session.rollback()
            return None
        run.status = "running"
        run.started_at = datetime.now(UTC)
        await session.commit()
        return run.id, list(run.scope or [])


async def run() -> None:
    settings = get_settings()
    log_format = settings.log_format
    if log_format == "auto":
        log_format = "json" if settings.app_env == "production" else "text"
    configure_logging(log_format)
    log = logging.getLogger("zyranet.worker")

    try:
        interval = max(10, settings.scan_interval_seconds)
        # A hard process/container kill cannot run scanner.scan()'s cleanup.
        # On worker start, close runs that have been abandoned well beyond a
        # normal sweep window so operators do not see permanent "running" jobs.
        abandoned_before = datetime.now(UTC) - timedelta(seconds=max(interval * 2, 900))
        async with async_session() as session:
            result = await session.execute(
                update(models.DiscoveryRun)
                .where(
                    models.DiscoveryRun.status == "running",
                    models.DiscoveryRun.started_at < abandoned_before,
                )
                .values(
                    status="failed",
                    error="worker restarted after the run stopped reporting",
                    completed_at=datetime.now(UTC),
                )
            )
            await session.commit()
            if result.rowcount:
                log.warning("marked %d abandoned discovery run(s) as failed", result.rowcount)

        if not settings.discovery_ready:
            async with async_session() as session:
                result = await session.execute(
                    update(models.DiscoveryRun)
                    .where(models.DiscoveryRun.status == "queued")
                    .values(
                        status="failed",
                        error="discovery is disabled or has no approved scan CIDRs",
                        completed_at=datetime.now(UTC),
                    )
                )
                await session.commit()
                if result.rowcount:
                    log.warning(
                        "closed %d queued discovery run(s) because discovery is not configured",
                        result.rowcount,
                    )
            log.info("device discovery is idle; enable it and configure approved scan CIDRs")
            while True:
                await asyncio.sleep(3600)

        loop = asyncio.get_running_loop()
        next_scheduled_scan = loop.time()
        while True:
            try:
                queued = await _claim_next_run()
                if queued is not None:
                    run_id, scope = queued
                    async with async_session() as session:
                        result = await scanner.scan(session, scope, run_id=run_id)
                    log.info("queued device scan complete: %s", result)
                    if loop.time() >= next_scheduled_scan:
                        next_scheduled_scan = loop.time() + interval
                    continue

                if loop.time() >= next_scheduled_scan:
                    async with async_session() as session:
                        result = await scanner.scan(session, settings.scan_cidr_list)
                    log.info("scheduled device scan complete: %s", result)
                    next_scheduled_scan = loop.time() + interval
                else:
                    await asyncio.sleep(min(2, max(0.1, next_scheduled_scan - loop.time())))
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("device scan failed")
                await asyncio.sleep(2)
    finally:
        await engine.dispose()


def main() -> None:
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
