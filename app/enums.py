"""Shared enums used by models and API."""
from __future__ import annotations

from enum import StrEnum


class VoucherStatus(StrEnum):
    unused = "unused"
    active = "active"
    expired = "expired"
    revoked = "revoked"


class TxnStatus(StrEnum):
    pending = "pending"
    paid = "paid"
    failed = "failed"


class Provider(StrEnum):
    flutterwave = "flutterwave"
    paystack = "paystack"
