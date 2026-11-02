"""ORM models for current operations data and selected RADIUS tables.

Legacy payment-era tables are intentionally not mapped so deployed records can
be retained without remaining part of the application runtime.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.sql.expression import text

from .db import Base

# Auto-incrementing integer PK: BIGSERIAL (Postgres) but INTEGER-rowid (SQLite),
# so the schema and the unit tests both work.
BigIntPK = BigInteger().with_variant(Integer(), "sqlite")


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
    __table_args__ = (
        Index("idx_devices_mac", "mac_address"),
        Index("idx_devices_online", "online"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    mac_address: Mapped[str] = mapped_column(Text, unique=True)
    ip_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    hostname: Mapped[str | None] = mapped_column(Text, nullable=True)
    vendor: Mapped[str | None] = mapped_column(Text, nullable=True)
    type: Mapped[str] = mapped_column(Text, default="unknown")
    source_ap: Mapped[str | None] = mapped_column(Text, nullable=True)
    online: Mapped[bool] = mapped_column(Boolean, default=False)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # --- Inventory fields (see docs/technical_docs1.md §19.4) ---
    label: Mapped[str | None] = mapped_column(String, nullable=True)
    model_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("device_models.id"), nullable=True
    )
    location_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("locations.id"), nullable=True
    )
    serial_number: Mapped[str | None] = mapped_column(String, nullable=True)
    hardware_revision: Mapped[str | None] = mapped_column(String, nullable=True)
    firmware: Mapped[str | None] = mapped_column(String, nullable=True)
    role: Mapped[str | None] = mapped_column(String, nullable=True)
    # unverified | good | degraded | faulty | retired
    condition: Mapped[str] = mapped_column(String, default="unverified")
    # confirmed | probable | unknown — strength of the identity evidence
    identity_confidence: Mapped[str] = mapped_column(String, default="unknown")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    sightings: Mapped[list[DeviceSighting]] = relationship(back_populates="device")
    model: Mapped[DeviceModel | None] = relationship(back_populates="devices")
    location: Mapped[Location | None] = relationship(back_populates="devices")
    interfaces: Mapped[list[DeviceInterface]] = relationship(
        back_populates="device", cascade="all, delete-orphan"
    )
    addresses: Mapped[list[DeviceAddress]] = relationship(
        back_populates="device", cascade="all, delete-orphan"
    )


class Location(Base):
    """Institution hierarchy: site > building > floor > room (any nesting)."""

    __tablename__ = "locations"
    __table_args__ = (Index("idx_locations_kind", "kind"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    parent_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("locations.id"), nullable=True
    )
    kind: Mapped[str] = mapped_column(String, default="building")  # site|building|floor|room|zone
    name: Mapped[str] = mapped_column(String)
    code: Mapped[str | None] = mapped_column(String, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    parent: Mapped[Location | None] = relationship(
        back_populates="children", remote_side="Location.id"
    )
    children: Mapped[list[Location]] = relationship(back_populates="parent")
    devices: Mapped[list[Device]] = relationship(back_populates="location")


class DeviceModel(Base):
    """Known hardware/firmware family with its declared capability matrix."""

    __tablename__ = "device_models"
    __table_args__ = (
        UniqueConstraint("vendor", "model", "hardware_revision", name="uq_model_revision"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    vendor: Mapped[str] = mapped_column(String)
    model: Mapped[str] = mapped_column(String)
    hardware_revision: Mapped[str] = mapped_column(String, default="")
    family: Mapped[str | None] = mapped_column(String, nullable=True)  # e.g. airMAX, UniFi
    management_protocols: Mapped[str | None] = mapped_column(String, nullable=True)
    # supported | experimental | unsupported | unknown
    support_status: Mapped[str] = mapped_column(String, default="unknown")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    devices: Mapped[list[Device]] = relationship(back_populates="model")
    capabilities: Mapped[list[DeviceCapability]] = relationship(
        back_populates="model", cascade="all, delete-orphan"
    )


class DeviceCapability(Base):
    """One operation a model/firmware can actually perform (adapter contract)."""

    __tablename__ = "device_capabilities"
    __table_args__ = (
        UniqueConstraint("model_id", "capability", name="uq_model_capability"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    model_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("device_models.id"))
    capability: Mapped[str] = mapped_column(String)  # identify|inspect|backup|configure|verify
    # read | read_write | guided_manual | unsupported
    support_level: Mapped[str] = mapped_column(String, default="read")
    adapter: Mapped[str | None] = mapped_column(String, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    model: Mapped[DeviceModel] = relationship(back_populates="capabilities")


class DeviceInterface(Base):
    """Physical/logical interface of a device (port, radio, VLAN)."""

    __tablename__ = "device_interfaces"
    __table_args__ = (UniqueConstraint("device_id", "name", name="uq_device_interface"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    device_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("devices.id"))
    name: Mapped[str] = mapped_column(String)  # eth0, ath0, vlan10 ...
    kind: Mapped[str] = mapped_column(String, default="ethernet")  # ethernet|radio|vlan|other
    mac_address: Mapped[str | None] = mapped_column(String, nullable=True)
    # up | down | unknown
    link_state: Mapped[str | None] = mapped_column(String, nullable=True)
    speed_mbps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    device: Mapped[Device] = relationship(back_populates="interfaces")


class DeviceAddress(Base):
    """Address history: configured vs observed, with validity windows."""

    __tablename__ = "device_addresses"
    __table_args__ = (Index("idx_device_addresses_address", "address"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    device_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("devices.id"))
    address: Mapped[str] = mapped_column(String)
    prefix_length: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # configured | observed | assigned
    source: Mapped[str] = mapped_column(String, default="observed")
    current: Mapped[bool] = mapped_column(Boolean, default=True)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    device: Mapped[Device] = relationship(back_populates="addresses")


class NetworkLink(Base):
    """A maintained connection between two inventoried device interfaces."""

    __tablename__ = "links"
    __table_args__ = (
        CheckConstraint("link_type IN ('physical', 'logical', 'wan')", name="ck_links_type"),
        CheckConstraint(
            "medium IN ('ethernet', 'fiber', 'wireless', 'wan', 'logical', 'other', 'unknown')",
            name="ck_links_medium",
        ),
        CheckConstraint(
            "verification_status IN ('reported', 'observed', 'associated', 'verified')",
            name="ck_links_verification_status",
        ),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_links_confidence",
        ),
        Index("idx_links_status", "verification_status"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    link_type: Mapped[str] = mapped_column(String(20), default="physical")
    medium: Mapped[str] = mapped_column(String(20), default="unknown")
    # reported | observed | associated | verified
    verification_status: Mapped[str] = mapped_column(String(20), default="reported")
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(80), default="manual")
    verification_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    endpoints: Mapped[list[LinkEndpoint]] = relationship(
        back_populates="link", cascade="all, delete-orphan", order_by="LinkEndpoint.side"
    )


class LinkEndpoint(Base):
    """One side of a normalized link, tied to a device and optional interface."""

    __tablename__ = "link_endpoints"
    __table_args__ = (
        UniqueConstraint("link_id", "side", name="uq_link_endpoint_side"),
        CheckConstraint("side IN ('A', 'B')", name="ck_link_endpoint_side"),
        Index("idx_link_endpoints_device", "device_id"),
        Index("idx_link_endpoints_interface", "interface_id"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    link_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("links.id", ondelete="CASCADE")
    )
    side: Mapped[str] = mapped_column(String(1))
    device_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("devices.id"))
    interface_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("device_interfaces.id", ondelete="SET NULL"), nullable=True
    )

    link: Mapped[NetworkLink] = relationship(back_populates="endpoints")
    device: Mapped[Device] = relationship()
    interface: Mapped[DeviceInterface | None] = relationship()


class TopologyObservation(Base):
    """Append-only evidence about a device, link, or both."""

    __tablename__ = "topology_observations"
    __table_args__ = (
        CheckConstraint(
            "device_id IS NOT NULL OR link_id IS NOT NULL",
            name="ck_topology_observation_target",
        ),
        CheckConstraint(
            "verification_status IN ('reported', 'observed', 'associated', 'verified')",
            name="ck_topology_observation_status",
        ),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_topology_observation_confidence",
        ),
        Index("idx_topology_observations_device", "device_id"),
        Index("idx_topology_observations_link", "link_id"),
        Index("idx_topology_observations_run", "discovery_run_id"),
        Index("idx_topology_observations_time", "observed_at"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    device_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("devices.id", ondelete="SET NULL"), nullable=True
    )
    link_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("links.id", ondelete="SET NULL"), nullable=True
    )
    discovery_run_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("discovery_runs.id", ondelete="SET NULL"), nullable=True
    )
    source: Mapped[str] = mapped_column(String(80))
    verification_status: Mapped[str] = mapped_column(String(20), default="observed")
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    device: Mapped[Device | None] = relationship()
    link: Mapped[NetworkLink | None] = relationship()
    discovery_run: Mapped[DiscoveryRun | None] = relationship()


class AuditEvent(Base):
    """Append-only administrative history (never updated/deleted by the app)."""

    __tablename__ = "audit_events"
    __table_args__ = (
        Index("idx_audit_created_at", "created_at"),
        Index("idx_audit_actor", "actor"),
        Index("idx_audit_action", "action"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    actor: Mapped[str] = mapped_column(String)
    role: Mapped[str | None] = mapped_column(String, nullable=True)
    action: Mapped[str] = mapped_column(String)  # e.g. device.create, auth.login
    entity_type: Mapped[str | None] = mapped_column(String, nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String, nullable=True)
    outcome: Mapped[str] = mapped_column(String, default="success")  # success | failure
    request_id: Mapped[str | None] = mapped_column(String, nullable=True)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


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
    __table_args__ = (
        Index("idx_sightings_device", "device_id"),
        Index("idx_sightings_seen_at", "seen_at"),
        Index("idx_sightings_run", "run_id"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    device_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("devices.id"))
    run_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("discovery_runs.id"), nullable=True
    )
    ip_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_ap: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String, default="neighbor_table")
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    online: Mapped[bool] = mapped_column(Boolean, default=True)
    seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    device: Mapped[Device] = relationship(back_populates="sightings")
    run: Mapped[DiscoveryRun | None] = relationship(back_populates="sightings")


class DiscoveryRun(Base):
    """One bounded discovery sweep and its aggregate evidence."""

    __tablename__ = "discovery_runs"
    __table_args__ = (
        Index("idx_discovery_runs_started_at", "started_at"),
        Index("idx_discovery_runs_status", "status"),
        Index(
            "uq_discovery_one_active_run",
            text("(1)"),
            unique=True,
            postgresql_where=text("status IN ('queued', 'running')"),
            sqlite_where=text("status IN ('queued', 'running')"),
        ),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    status: Mapped[str] = mapped_column(String, default="running")
    scope: Mapped[list] = mapped_column(JSON, default=list)
    requested_by: Mapped[str | None] = mapped_column(String, nullable=True)
    targets_total: Mapped[int] = mapped_column(Integer, default=0)
    probes_responded: Mapped[int] = mapped_column(Integer, default=0)
    probe_errors: Mapped[int] = mapped_column(Integer, default=0)
    devices_observed: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    sightings: Mapped[list[DeviceSighting]] = relationship(back_populates="run")
