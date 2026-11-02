"""FastAPI application entrypoint."""
from __future__ import annotations

import logging
import secrets
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import text
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .config import get_settings
from .db import engine
from .logging_config import configure_logging
from .routers import auth, devices, network
from .routers.v1 import router as v1_router

settings = get_settings()

_log_format = settings.log_format
if _log_format == "auto":
    _log_format = "json" if settings.app_env == "production" else "text"
configure_logging(_log_format)

log = logging.getLogger("zyranet.app")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        yield
    finally:
        await engine.dispose()


app = FastAPI(title="Zyranet", version="0.1.0", lifespan=lifespan)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_host_list)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["authorization", "content-type", "x-request-id"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    """Attach a request ID and log every request with its duration."""
    request_id = request.headers.get("x-request-id") or secrets.token_hex(8)
    request.state.request_id = request_id
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        log.exception(
            "unhandled error",
            extra={"request_id": request_id, "method": request.method, "path": request.url.path},
        )
        raise
    duration_ms = int((time.perf_counter() - start) * 1000)
    response.headers["X-Request-ID"] = request_id
    log.info(
        "%s %s -> %s (%dms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    return response


# Compatibility APIs for existing network discovery clients.
app.include_router(auth.router, prefix="/api")
app.include_router(devices.router, prefix="/api")
app.include_router(network.router, prefix="/api")
# Versioned ICT operations API.
app.include_router(v1_router)

# React SPA (frontend/dist copied here by the Docker build). Backend-only dev
# checkouts use the Vite dev server instead.
_SPA_DIR = Path(__file__).resolve().parent / "static" / "spa"


@app.get("/admin", include_in_schema=False)
async def admin_dashboard():
    return RedirectResponse("/", status_code=307)


@app.get("/health", tags=["health"])
async def health():
    """Liveness endpoint: the API process is accepting requests."""
    return {"status": "ok"}


@app.get("/health/ready", tags=["health"])
async def readiness():
    """Readiness endpoint: the API can reach its required database."""
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception:
        log.exception("readiness check failed: database unavailable")
        raise HTTPException(
            status_code=503, detail={"status": "not_ready", "database": "down"}
        ) from None
    return {"status": "ready", "database": "ok"}


@app.get("/{full_path:path}", include_in_schema=False)
async def spa_catch_all(full_path: str):
    """Serve the React dashboard for every non-API GET route (client routing)."""
    # Never shadow API paths: unknown ones must 404 as JSON, not get the SPA.
    if full_path == "api" or full_path.startswith(("api/", "static/")):
        raise HTTPException(status_code=404)
    if not _SPA_DIR.is_dir():
        raise HTTPException(status_code=503, detail="Frontend build not found")
    if full_path:
        candidate = _SPA_DIR / full_path
        try:
            resolved = candidate.resolve()
            resolved.relative_to(_SPA_DIR.resolve())
        except (OSError, ValueError):
            raise HTTPException(status_code=404) from None
        if resolved.is_file():
            return FileResponse(resolved)
        # Unknown asset (has an extension) -> 404, not the SPA shell.
        if "." in Path(full_path).name:
            raise HTTPException(status_code=404)
    return FileResponse(_SPA_DIR / "index.html")
