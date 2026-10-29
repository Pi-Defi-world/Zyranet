"""Flutterwave payment adapter (v3 API)."""
from __future__ import annotations

from typing import Any

import httpx

from ...config import get_settings
from .base import PaymentInit, PaymentProvider, PaymentStatus

_BASE = "https://api.flutterwave.com/v3"
_TIMEOUT = httpx.Timeout(15.0)


class FlutterwaveProvider(PaymentProvider):
    name = "flutterwave"

    def __init__(self) -> None:
        self._settings = get_settings()
        self._key = self._settings.flutterwave_secret_key

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
            "tx_ref": reference,
            "amount": amount_kobo / 100,
            "currency": currency,
            "redirect_url": f"{self._settings.public_base_url}/payments/flutterwave/callback",
            "customizations": {"title": "Zyranet"},
            "meta": metadata or {},
        }
        if customer_email:
            payload["customer"] = {"email": customer_email, "name": customer_email}

        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{_BASE}/payments",
                json=payload,
                headers={"Authorization": f"Bearer {self._key}"},
            )
            resp.raise_for_status()
            body = resp.json().get("data", {})
            checkout_url = body.get("link") or ""
            return PaymentInit(reference=reference, checkout_url=checkout_url)

    async def verify(self, provider_ref: str) -> PaymentStatus:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{_BASE}/transactions/{provider_ref}/verify",
                headers={"Authorization": f"Bearer {self._key}"},
            )
            resp.raise_for_status()
            data = resp.json().get("data", {})
        paid = str(data.get("status", "")).lower() == "successful"
        amount_kobo = int(round(float(data.get("amount", 0) or 0) * 100))
        return PaymentStatus(
            paid=paid,
            provider_ref=provider_ref,
            amount_kobo=amount_kobo,
            raw=data,
        )
