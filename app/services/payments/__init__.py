"""Payment provider adapters (Flutterwave, Paystack)."""
from .base import PaymentInit, PaymentProvider, PaymentStatus
from .flutterwave import FlutterwaveProvider
from .paystack import PaystackProvider

__all__ = [
    "PaymentProvider",
    "PaymentInit",
    "PaymentStatus",
    "FlutterwaveProvider",
    "PaystackProvider",
    "get_provider",
]


def get_provider(name: str) -> PaymentProvider:
    if name == "flutterwave":
        return FlutterwaveProvider()
    if name == "paystack":
        return PaystackProvider()
    raise ValueError(f"Unknown payment provider: {name}")
