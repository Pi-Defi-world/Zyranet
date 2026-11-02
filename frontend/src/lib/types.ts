/** Shared types mirroring the /api/v1 OpenAPI schemas. */

export interface CurrentUser {
  username: string
  role: string
}

export interface Location {
  id: number
  parent_id: number | null
  kind: string
  name: string
  code: string | null
  notes: string | null
}

export interface Capability {
  id: number
  model_id: number
  capability: string
  support_level: string
  adapter: string | null
  notes: string | null
}

export interface DeviceModel {
  id: number
  vendor: string
  model: string
  hardware_revision: string
  family: string | null
  management_protocols: string | null
  support_status: string
  notes: string | null
  capabilities: Capability[]
}

export interface DeviceInterface {
  id: number
  device_id: number
  name: string
  kind: string
  mac_address: string | null
  link_state: string | null
  speed_mbps: number | null
  notes: string | null
}

export interface DeviceAddress {
  id: number
  device_id: number
  address: string
  prefix_length: number | null
  source: string
  current: boolean
  first_seen: string
  last_seen: string
}

export interface Device {
  id: number
  mac_address: string
  label: string | null
  vendor: string | null
  type: string
  ip_address: string | null
  hostname: string | null
  model_id: number | null
  location_id: number | null
  serial_number: string | null
  hardware_revision: string | null
  firmware: string | null
  role: string | null
  condition: string
  identity_confidence: string
  notes: string | null
  online: boolean
  observation_status: 'observed' | 'stale' | 'unknown'
  first_seen: string
  last_seen: string
  model: DeviceModel | null
  location: Location | null
}

export interface DiscoveryRun {
  id: number
  status: 'queued' | 'running' | 'succeeded' | 'partial' | 'failed'
  scope: string[]
  requested_by: string | null
  targets_total: number
  probes_responded: number
  probe_errors: number
  devices_observed: number
  error: string | null
  created_at: string
  started_at: string | null
  completed_at: string | null
}

export interface DiscoveryObservation {
  id: number
  device_id: number
  mac_address: string
  label: string | null
  vendor: string | null
  type: string
  ip_address: string | null
  source: string
  evidence: Record<string, unknown>
  seen_at: string
}

export interface DiscoveryObservationPage {
  total: number
  items: DiscoveryObservation[]
}

export interface HardwareIdentity {
  adapter: string
  protocol: string
  host: string
  sys_name: string | null
  sys_descr: string | null
  sys_object_id: string | null
  sys_uptime_ticks: number | null
  collected_at: string
}

export interface OverviewSummary {
  devices: number
  observed_devices: number
  stale_devices: number
  unknown_devices: number
  locations: number
  latest_discovery: DiscoveryRun | null
}

export interface TopologyZone {
  id: string
  label: string
  color: string
}

export interface TopologyNode {
  id: string
  label: string
  group: string
  shape: string
  kind: string
  title: string
  meta: Record<string, unknown>
  x?: number
  y?: number
}

export interface TopologyEdge {
  id: string
  from: string
  to: string
  label?: string
  dashes?: boolean
  color?: { color?: string }
  meta?: Record<string, unknown>
}

export interface TopologyGraph {
  meta: Record<string, unknown> | null
  zones: TopologyZone[]
  nodes: TopologyNode[]
  edges: TopologyEdge[]
  switch_ports: Record<string, unknown[]>
  stats: {
    infrastructure_nodes: number
    observed_devices: number
    links: number
    truncated?: boolean
    total_devices?: number
  }
}

export interface NetworkLinkEndpoint {
  id: number
  side: 'A' | 'B'
  device_id: number
  interface_id: number | null
  device_label: string
  mac_address: string
  interface_name: string | null
}

export interface NetworkLink {
  id: number
  label: string | null
  link_type: 'physical' | 'logical' | 'wan'
  medium: 'ethernet' | 'fiber' | 'wireless' | 'wan' | 'logical' | 'other' | 'unknown'
  verification_status: 'reported' | 'observed' | 'associated' | 'verified'
  confidence: number | null
  source: string
  verification_evidence: string | null
  evidence: Record<string, unknown>
  notes: string | null
  created_by: string | null
  created_at: string
  updated_at: string
  endpoints: NetworkLinkEndpoint[]
}

export interface NetworkLinkInput {
  label?: string | null
  link_type: NetworkLink['link_type']
  medium: NetworkLink['medium']
  verification_status: NetworkLink['verification_status']
  confidence?: number | null
  source: string
  verification_evidence?: string | null
  evidence?: Record<string, unknown>
  notes?: string | null
  endpoints: Array<{
    side: 'A' | 'B'
    device_id: number
    interface_id?: number | null
  }>
}

export type NetworkLinkPatch = Partial<NetworkLinkInput>

export interface TopologyObservation {
  id: number
  device_id: number | null
  link_id: number | null
  discovery_run_id: number | null
  source: string
  verification_status: 'reported' | 'observed' | 'associated' | 'verified'
  confidence: number | null
  evidence: Record<string, unknown>
  notes: string | null
  observed_at: string
  created_at: string
}

export interface TopologyObservationInput {
  device_id?: number | null
  link_id?: number | null
  discovery_run_id?: number | null
  source: string
  verification_status: TopologyObservation['verification_status']
  confidence?: number | null
  evidence: Record<string, unknown>
  notes?: string | null
}

export interface AuditEvent {
  id: number
  actor: string
  role: string | null
  action: string
  entity_type: string | null
  entity_id: string | null
  outcome: string
  request_id: string | null
  detail: Record<string, unknown>
  created_at: string
}

export interface Page<T> {
  total: number
  items: T[]
}

export interface DeviceInput {
  mac_address: string
  label?: string | null
  vendor?: string | null
  type?: string
  ip_address?: string | null
  hostname?: string | null
  model_id?: number | null
  location_id?: number | null
  serial_number?: string | null
  hardware_revision?: string | null
  firmware?: string | null
  role?: string | null
  condition?: string
  identity_confidence?: string
  notes?: string | null
}

export interface LocationInput {
  kind: string
  name: string
  parent_id?: number | null
  code?: string | null
  notes?: string | null
}
