"""Pydantic request/response schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .enums import Provider, TxnStatus, VoucherStatus


class PlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    duration_seconds: int
    price_kobo: int
    price_currency: str
    active: bool


class VoucherCreate(BaseModel):
    plan_name: str
    telegram_chat_id: int | None = None
    phone: str | None = None


class VoucherOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    code: str
    plan_name: str
    status: VoucherStatus
    valid_from: datetime | None
    valid_until: datetime | None


class PurchaseRequest(BaseModel):
    plan_name: str
    telegram_chat_id: int | None = None
    phone: str | None = None
    provider: Provider = Provider.paystack


class PurchaseHandle(BaseModel):
    id: int
    provider: Provider
    provider_ref: str | None
    status: TxnStatus
    checkout_url: str | None = None


class PaymentWebhook(BaseModel):
    provider: Provider
    reference: str
    amount_kobo: int | None = None
    status: str = "success"
    # provider-native payload passthrough for verification
    data: dict | None = None


class ActivateRequest(BaseModel):
    code: str
    mac_address: str = Field(pattern=r"^[0-9a-fA-F]{2}(:[0-9a-fA-F]{2}){5}$")


class RedeemResult(BaseModel):
    accepted: bool
    reason: str | None = None
    remaining_seconds: int | None = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    username: str
    password: str


class TopologyNodeIn(BaseModel):
    id: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9._-]+$")
    label: str = Field(min_length=1, max_length=120)
    kind: str = "unknown"
    zone: str = "core"
    subtitle: str | None = None
    mgmt_ip: str | None = None
    ssid: str | None = None
    ports: int | None = Field(None, ge=1, le=128)
    fixed: dict[str, float] | None = None


class TopologyLinkIn(BaseModel):
    id: str | None = None
    source: str
    target: str
    source_port: str | None = None
    target_port: str | None = None
    medium: str = "ethernet"
    label: str | None = None


class TopologyPositionsIn(BaseModel):
    positions: dict[str, dict[str, float]]


class TopologyApplyDiscoveryIn(BaseModel):
    links: list[TopologyLinkIn]
