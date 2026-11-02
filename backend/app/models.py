"""SQLAlchemy ORM models. Mirrors db/schema.sql."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from . import enums
from .db import Base

# Auto-incrementing integer PK: BIGSERIAL (Postgres) but INTEGER-rowid (SQLite),
# so the schema and the unit tests both work.
BigIntPK = BigInteger().with_variant(Integer(), "sqlite")


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    duration_seconds: Mapped[int] = mapped_column(Integer)
    price_kobo: Mapped[int] = mapped_column(Integer)
    price_currency: Mapped[str] = mapped_column(String, default="NGN")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    vouchers: Mapped[list[Voucher]] = relationship(back_populates="plan")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, nullable=True)
    telegram_username: Mapped[str | None] = mapped_column(String, nullable=True)
    telegram_name: Mapped[str | None] = mapped_column(String, nullable=True)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    flutterwave_customer_id: Mapped[str | None] = mapped_column(String, nullable=True)
    paystack_customer_id: Mapped[str | None] = mapped_column(String, nullable=True)
    is_staff: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    vouchers: Mapped[list[Voucher]] = relationship(back_populates="user")


class Voucher(Base):
    __tablename__ = "vouchers"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    code: Mapped[str] = mapped_column(String, unique=True)
    plan_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("plans.id"))
    user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[enums.VoucherStatus] = mapped_column(
        SAEnum(enums.VoucherStatus, name="voucher_status"), default=enums.VoucherStatus.unused
    )
    max_devices: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    plan: Mapped[Plan] = relationship(back_populates="vouchers")
    user: Mapped[User | None] = relationship(back_populates="vouchers")
    transactions: Mapped[list[Transaction]] = relationship(back_populates="voucher")


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    voucher_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("vouchers.id"))
    user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    provider: Mapped[enums.Provider] = mapped_column(SAEnum(enums.Provider, name="txn_provider"))
    provider_ref: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    amount_kobo: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String, default="NGN")
    status: Mapped[enums.TxnStatus] = mapped_column(
        SAEnum(enums.TxnStatus, name="txn_status"), default=enums.TxnStatus.pending
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    voucher: Mapped[Voucher] = relationship(back_populates="transactions")
    user: Mapped[User | None] = relationship()


class RedeemedDevice(Base):
    __tablename__ = "redeemed_devices"
    __table_args__ = (UniqueConstraint("voucher_id", "mac_address", name="uq_voucher_mac"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    voucher_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("vouchers.id"))
    mac_address: Mapped[str] = mapped_column(Text)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class OtpCode(Base):
    __tablename__ = "otp_codes"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    phone: Mapped[str] = mapped_column(Text)
    code: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RadCheck(Base):
    __tablename__ = "radcheck"
    __table_args__ = (Index("idx_radcheck_username", "username"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    username: Mapped[str] = mapped_column(String, default="")
    attribute: Mapped[str] = mapped_column(String, default="")
    op: Mapped[str] = mapped_column(String(2), default="==")
    value: Mapped[str] = mapped_column(String, default="")


class RadReply(Base):
    __tablename__ = "radreply"
    __table_args__ = (Index("idx_radreply_username", "username"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    username: Mapped[str] = mapped_column(String, default="")
    attribute: Mapped[str] = mapped_column(String, default="")
    op: Mapped[str] = mapped_column(String(2), default="==")
    value: Mapped[str] = mapped_column(String, default="")


class RadAcct(Base):
    __tablename__ = "radacct"
    __table_args__ = (Index("idx_radacct_username", "username"),)

    radacctid: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    acctsessionid: Mapped[str] = mapped_column(String, default="")
    acctuniqueid: Mapped[str] = mapped_column(String, default="")
    username: Mapped[str] = mapped_column(String, default="")
    groupname: Mapped[str] = mapped_column(String, default="")
    realm: Mapped[str] = mapped_column(String, default="")
    nasipaddress: Mapped[str] = mapped_column(String, default="")
    nasportid: Mapped[str] = mapped_column(String, default="")
    nasporttype: Mapped[str] = mapped_column(String, default="")
    acctstarttime: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acctstoptime: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acctsessiontime: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    acctauthentic: Mapped[str] = mapped_column(String, default="")
    acctinputoctets: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    acctoutputoctets: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    calledstationid: Mapped[str] = mapped_column(String, default="")
    callingstationid: Mapped[str] = mapped_column(String, default="")
    acctterminatecause: Mapped[str] = mapped_column(String, default="")
    framedipaddress: Mapped[str] = mapped_column(String, default="")


class Device(Base):
    __tablename__ = "devices"
    __table_args__ = (Index("idx_devices_online", "online"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    mac_address: Mapped[str] = mapped_column(String, unique=True)
    ip_address: Mapped[str | None] = mapped_column(String, nullable=True)
    hostname: Mapped[str | None] = mapped_column(String, nullable=True)
    vendor: Mapped[str | None] = mapped_column(String, nullable=True)
    type: Mapped[str] = mapped_column(String, default="unknown")
    source_ap: Mapped[str | None] = mapped_column(String, nullable=True)
    online: Mapped[bool] = mapped_column(Boolean, default=False)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    sightings: Mapped[list[DeviceSighting]] = relationship(back_populates="device")


class TopologyDocument(Base):
    """Single-row JSON document for the admin network map (editable via API)."""

    __tablename__ = "topology_document"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    data: Mapped[str] = mapped_column(Text, default="{}")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class DeviceSighting(Base):
    __tablename__ = "device_sightings"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    device_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("devices.id"))
    ip_address: Mapped[str | None] = mapped_column(String, nullable=True)
    source_ap: Mapped[str | None] = mapped_column(String, nullable=True)
    online: Mapped[bool] = mapped_column(Boolean, default=True)
    seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    device: Mapped[Device] = relationship(back_populates="sightings")
