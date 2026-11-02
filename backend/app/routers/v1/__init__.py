"""Versioned ICT operations API (`/api/v1`).

Conventions (docs/technical_docs1.md §19.5): plural resources, pagination,
Pydantic schemas only, role-checked writes and audit events.
"""
from __future__ import annotations

from fastapi import APIRouter

from . import audit, auth, discovery, hardware, inventory, topology

router = APIRouter(prefix="/api/v1")
router.include_router(auth.router)
router.include_router(inventory.router)
router.include_router(discovery.router)
router.include_router(hardware.router)
router.include_router(audit.router)
router.include_router(topology.router)

__all__ = ["router"]
