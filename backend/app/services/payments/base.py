"""Payment provider abstract interface + shared dataclasses."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class PaymentInit:
    reference: str
    checkout_url: str


@dataclass
class PaymentStatus:
    paid: bool
    provider_ref: str
    amount_kobo: int | None = None
    raw: dict[str, Any] | None = None


class PaymentProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def initialize(
        self,
        *,
        reference: str,
        amount_kobo: int,
        currency: str,
        customer_email: str | None,
        phone: str | None,
        metadata: dict[str, Any] | None = None,
    ) -> PaymentInit: ...

    @abstractmethod
    async def verify(self, provider_ref: str) -> PaymentStatus: ...

    def normalize_email(self, phone: str | None, telegram_username: str | None) -> str | None:
        """Payment providers require an email; fall back to a placeholder."""
        if telegram_username:
            return f"{telegram_username}@zyranet.local"
        if phone:
            return f"{phone}@zyranet.local"
        return None
