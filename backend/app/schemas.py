"""Pydantic request/response schemas."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field

from .config import get_settings

LocationKind = Literal["site", "building", "floor", "room", "zone"]
Condition = Literal["unverified", "good", "degraded", "faulty", "retired"]
IdentityConfidence = Literal["confirmed", "probable", "unknown"]
SupportStatus = Literal["supported", "experimental", "unsupported", "unknown"]
SupportLevel = Literal["read", "read_write", "guided_manual", "unsupported"]


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    username: str
    password: str


class CurrentUserOut(BaseModel):
    username: str
    role: str


# ---------------------------------------------------------------------------
# v1 inventory API (see docs/technical_docs1.md §19.4, §19.5)
# ---------------------------------------------------------------------------


class LocationIn(BaseModel):
    parent_id: int | None = None
    kind: LocationKind = "building"
    name: str = Field(min_length=1, max_length=120)
    code: str | None = Field(None, max_length=40)
    notes: str | None = None


class LocationPatch(BaseModel):
    parent_id: int | None = None
    kind: LocationKind | None = None
    name: str | None = Field(None, min_length=1, max_length=120)
    code: str | None = Field(None, max_length=40)
    notes: str | None = None


class LocationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    parent_id: int | None
    kind: str
    name: str
    code: str | None
    notes: str | None


class CapabilityIn(BaseModel):
    capability: str = Field(min_length=1, max_length=60)
    support_level: SupportLevel = "read"
    adapter: str | None = None
    notes: str | None = None


class CapabilityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    model_id: int
    capability: str
    support_level: str
    adapter: str | None
    notes: str | None


class DeviceModelIn(BaseModel):
    vendor: str = Field(min_length=1, max_length=80)
    model: str = Field(min_length=1, max_length=120)
    hardware_revision: str = Field(default="", max_length=40)
    family: str | None = Field(None, max_length=80)
    management_protocols: str | None = Field(None, max_length=120)
    support_status: SupportStatus = "unknown"
    notes: str | None = None
    capabilities: list[CapabilityIn] = []


class DeviceModelPatch(BaseModel):
    vendor: str | None = Field(None, min_length=1, max_length=80)
    model: str | None = Field(None, min_length=1, max_length=120)
    hardware_revision: str | None = Field(None, max_length=40)
    family: str | None = Field(None, max_length=80)
    management_protocols: str | None = Field(None, max_length=120)
    support_status: SupportStatus | None = None
    notes: str | None = None


class DeviceModelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vendor: str
    model: str
    hardware_revision: str
    family: str | None
    management_protocols: str | None
    support_status: str
    notes: str | None
    capabilities: list[CapabilityOut] = []


class DeviceInterfaceIn(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    kind: Literal["ethernet", "radio", "vlan", "other"] = "ethernet"
    mac_address: str | None = Field(
        None, pattern=r"^[0-9a-fA-F]{2}(:[0-9a-fA-F]{2}){5}$"
    )
    link_state: Literal["up", "down", "unknown"] | None = None
    speed_mbps: int | None = Field(None, ge=0)
    notes: str | None = None


class DeviceInterfaceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: int
    name: str
    kind: str
    mac_address: str | None
    link_state: str | None
    speed_mbps: int | None
    notes: str | None


class DeviceAddressIn(BaseModel):
    address: str = Field(min_length=1, max_length=45)
    prefix_length: int | None = Field(None, ge=0, le=128)
    source: Literal["configured", "observed", "assigned"] = "observed"


class DeviceAddressOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: int
    address: str
    prefix_length: int | None
    source: str
    current: bool
    first_seen: datetime
    last_seen: datetime


class DeviceIn(BaseModel):
    mac_address: str = Field(pattern=r"^[0-9a-fA-F]{2}(:[0-9a-fA-F]{2}){5}$")
    label: str | None = Field(None, max_length=120)
    vendor: str | None = Field(None, max_length=80)
    type: str = Field(default="unknown", max_length=40)
    ip_address: str | None = Field(None, max_length=45)
    hostname: str | None = Field(None, max_length=120)
    model_id: int | None = None
    location_id: int | None = None
    serial_number: str | None = Field(None, max_length=80)
    hardware_revision: str | None = Field(None, max_length=40)
    firmware: str | None = Field(None, max_length=80)
    role: str | None = Field(None, max_length=60)
    condition: Condition = "unverified"
    identity_confidence: IdentityConfidence = "unknown"
    notes: str | None = None
    interfaces: list[DeviceInterfaceIn] = []


class DevicePatch(BaseModel):
    label: str | None = Field(None, max_length=120)
    vendor: str | None = Field(None, max_length=80)
    type: str | None = Field(None, max_length=40)
    ip_address: str | None = Field(None, max_length=45)
    hostname: str | None = Field(None, max_length=120)
    model_id: int | None = None
    location_id: int | None = None
    serial_number: str | None = Field(None, max_length=80)
    hardware_revision: str | None = Field(None, max_length=40)
    firmware: str | None = Field(None, max_length=80)
    role: str | None = Field(None, max_length=60)
    condition: Condition | None = None
    identity_confidence: IdentityConfidence | None = None
    notes: str | None = None


class DeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    mac_address: str
    label: str | None
    vendor: str | None
    type: str
    ip_address: str | None
    hostname: str | None
    model_id: int | None
    location_id: int | None
    serial_number: str | None
    hardware_revision: str | None
    firmware: str | None
    role: str | None
    condition: str
    identity_confidence: str
    notes: str | None
    online: bool
    first_seen: datetime
    last_seen: datetime
    model: DeviceModelOut | None = None
    location: LocationOut | None = None

    @computed_field
    @property
    def observation_status(self) -> Literal["observed", "stale", "unknown"]:
        if not self.online:
            return "unknown"
        last_seen = self.last_seen
        if last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=UTC)
        age_seconds = (datetime.now(UTC) - last_seen).total_seconds()
        threshold = max(60, get_settings().device_stale_after_seconds)
        return "observed" if age_seconds <= threshold else "stale"


class AuditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor: str
    role: str | None
    action: str
    entity_type: str | None
    entity_id: str | None
    outcome: str
    request_id: str | None
    detail: dict
    created_at: datetime


class DevicePageOut(BaseModel):
    total: int
    items: list[DeviceOut]


class DeviceModelPageOut(BaseModel):
    total: int
    items: list[DeviceModelOut]


class AuditPageOut(BaseModel):
    total: int
    items: list[AuditEventOut]


class DiscoveryRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: Literal["queued", "running", "succeeded", "partial", "failed"]
    scope: list[str]
    requested_by: str | None
    targets_total: int
    probes_responded: int
    probe_errors: int
    devices_observed: int
    error: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class DiscoveryRunPageOut(BaseModel):
    total: int
    items: list[DiscoveryRunOut]


class DiscoveryObservationOut(BaseModel):
    id: int
    device_id: int
    mac_address: str
    label: str | None
    vendor: str | None
    type: str
    ip_address: str | None
    source: str
    evidence: dict
    seen_at: datetime


class DiscoveryObservationPageOut(BaseModel):
    total: int
    items: list[DiscoveryObservationOut]


class AdapterCapabilityOut(BaseModel):
    name: str
    access: Literal["read", "write"]
    description: str


class AdapterDescriptorOut(BaseModel):
    id: str
    name: str
    protocol: str
    vendor_scope: str
    capabilities: list[AdapterCapabilityOut]


class HardwareIdentityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    adapter: str
    protocol: str
    host: str
    sys_name: str | None
    sys_descr: str | None
    sys_object_id: str | None
    sys_uptime_ticks: int | None
    collected_at: datetime


class OverviewSummaryOut(BaseModel):
    devices: int
    observed_devices: int
    stale_devices: int
    unknown_devices: int
    locations: int
    latest_discovery: DiscoveryRunOut | None


# ---------------------------------------------------------------------------
# Normalized topology resources (legacy JSON document routes remain compatible)
# ---------------------------------------------------------------------------

LinkStatus = Literal["reported", "observed", "associated", "verified"]
LinkType = Literal["physical", "logical", "wan"]
LinkMedium = Literal["ethernet", "fiber", "wireless", "wan", "logical", "other", "unknown"]


class LinkEndpointIn(BaseModel):
    side: Literal["A", "B"]
    device_id: int = Field(gt=0)
    interface_id: int | None = Field(None, gt=0)


class LinkEndpointOut(BaseModel):
    id: int
    side: Literal["A", "B"]
    device_id: int
    interface_id: int | None
    device_label: str
    mac_address: str
    interface_name: str | None


class NetworkLinkIn(BaseModel):
    label: str | None = Field(None, max_length=120)
    link_type: LinkType = "physical"
    medium: LinkMedium = "unknown"
    verification_status: LinkStatus = "reported"
    confidence: float | None = Field(None, ge=0, le=1)
    source: str = Field(default="manual", min_length=1, max_length=80)
    verification_evidence: str | None = Field(None, max_length=2000)
    evidence: dict = Field(default_factory=dict)
    notes: str | None = None
    endpoints: list[LinkEndpointIn] = Field(min_length=2, max_length=2)


class NetworkLinkPatch(BaseModel):
    label: str | None = Field(None, max_length=120)
    link_type: LinkType | None = None
    medium: LinkMedium | None = None
    verification_status: LinkStatus | None = None
    confidence: float | None = Field(None, ge=0, le=1)
    source: str | None = Field(None, min_length=1, max_length=80)
    verification_evidence: str | None = Field(None, max_length=2000)
    evidence: dict | None = None
    notes: str | None = None
    endpoints: list[LinkEndpointIn] | None = Field(None, min_length=2, max_length=2)


class NetworkLinkOut(BaseModel):
    id: int
    label: str | None
    link_type: str
    medium: str
    verification_status: LinkStatus
    confidence: float | None
    source: str
    verification_evidence: str | None
    evidence: dict
    notes: str | None
    created_by: str | None
    created_at: datetime
    updated_at: datetime
    endpoints: list[LinkEndpointOut]


class NetworkLinkPageOut(BaseModel):
    total: int
    items: list[NetworkLinkOut]


class TopologyObservationIn(BaseModel):
    device_id: int | None = Field(None, gt=0)
    link_id: int | None = Field(None, gt=0)
    discovery_run_id: int | None = Field(None, gt=0)
    source: str = Field(min_length=1, max_length=80)
    verification_status: LinkStatus = "observed"
    confidence: float | None = Field(None, ge=0, le=1)
    evidence: dict = Field(default_factory=dict)
    notes: str | None = None
    observed_at: datetime | None = None


class TopologyObservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: int | None
    link_id: int | None
    discovery_run_id: int | None
    source: str
    verification_status: LinkStatus
    confidence: float | None
    evidence: dict
    notes: str | None
    observed_at: datetime
    created_at: datetime


class TopologyObservationPageOut(BaseModel):
    total: int
    items: list[TopologyObservationOut]


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
