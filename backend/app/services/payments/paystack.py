"""Paystack payment adapter (v2 API)."""
from __future__ import annotations

from typing import Any

import httpx

from ...config import get_settings
from .base import PaymentInit, PaymentProvider, PaymentStatus

_BASE = "https://api.paystack.co"
_TIMEOUT = httpx.Timeout(15.0)


class PaystackProvider(PaymentProvider):
    name = "paystack"

    def __init__(self) -> None:
        self._settings = get_settings()
        self._key = self._settings.paystack_secret_key

    async def initialize(
        self,
        *,
        reference: str,
        amount_kobo: int,
        currency: str,
        customer_email: str | None,
        phone: str | None,
        metadata: dict[str, Any] | None = None,
    ) -> PaymentInit:
        payload = {
            "reference": reference,
            "amount": amount_kobo,
            "currency": currency,
            "email": customer_email or "guest@zyranet.local",
            "callback_url": f"{self._settings.public_base_url}/payments/paystack/callback",
            "metadata": {**metadata, "phone": phone} if (metadata or phone) else metadata,
        }
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{_BASE}/transaction/initialize",
                json=payload,
                headers={"Authorization": f"Bearer {self._key}"},
            )
            resp.raise_for_status()
            data = resp.json().get("data", {})
            return PaymentInit(
                reference=reference, checkout_url=data.get("authorization_url") or ""
            )

    async def verify(self, provider_ref: str) -> PaymentStatus:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{_BASE}/transaction/verify/{provider_ref}",
                headers={"Authorization": f"Bearer {self._key}"},
            )
            resp.raise_for_status()
            data = resp.json().get("data", {})
        paid = str(data.get("status", "")).lower() == "success"
        return PaymentStatus(
            paid=paid,
            provider_ref=provider_ref,
            amount_kobo=int(data.get("amount", 0) or 0),
            raw=data,
        )
