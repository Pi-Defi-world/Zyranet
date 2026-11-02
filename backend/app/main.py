"""FastAPI application entrypoint."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .db import async_session, engine
from .routers import admin, auth, devices, network, payments, vouchers
from .services import scanner

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("zyranet.app")


async def _scan_loop() -> None:
    s = get_settings()
    if not s.scan_enabled:
        return
    while True:
        try:
            async with async_session() as session:
                result = await scanner.scan(session, s.scan_cidr_list)
                log.info("device scan complete: %s", result)
        except Exception:  # pragma: no cover - keep the loop alive
            log.exception("device scan failed")
        await asyncio.sleep(s.scan_interval_seconds)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_scan_loop())
    try:
        yield
    finally:
        task.cancel()
        await engine.dispose()


settings = get_settings()
app = FastAPI(title="Zyranet", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(vouchers.router, prefix="/api")
app.include_router(payments.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(devices.router, prefix="/api")
app.include_router(network.router, prefix="/api")

_STATIC = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=_STATIC), name="static")


@app.get("/admin", include_in_schema=False)
async def admin_dashboard():
    return FileResponse(_STATIC / "admin.html")


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}
