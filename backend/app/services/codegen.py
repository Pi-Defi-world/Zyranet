"""Voucher code generation."""
from __future__ import annotations

import secrets

# Unambiguous characters (no 0/O/1/I/l) to avoid mistypes at input.
_ALPHABET = "ACDEFGHJKLMNPQRSTUVWXYZ23456789"


def make_voucher_code(length: int = 12, group: bool = True) -> str:
    raw = "".join(secrets.choice(_ALPHABET) for _ in range(length))
    if not group:
        return raw
    parts = [raw[i : i + 4] for i in range(0, len(raw), 4)]
    return "-".join(parts)
