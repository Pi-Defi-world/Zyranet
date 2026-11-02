/** Thin typed fetch client for the Zyranet /api/v1 surface. */
import type {
  AuditEvent,
  CurrentUser,
  Device,
  DeviceAddress,
  DeviceInput,
  DeviceInterface,
  DeviceModel,
  DiscoveryObservationPage,
  DiscoveryRun,
  HardwareIdentity,
  Location,
  LocationInput,
  NetworkLink,
  NetworkLinkInput,
  NetworkLinkPatch,
  OverviewSummary,
  Page,
  TopologyObservation,
  TopologyObservationInput,
  TopologyGraph,
} from './types'

const TOKEN_KEY = 'zyranet_token'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  headers.set('Accept', 'application/json')
  if (init.body) headers.set('Content-Type', 'application/json')
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)

  const resp = await fetch(`/api/v1${path}`, { ...init, headers })
  if (resp.status === 204) return undefined as T

  const text = await resp.text()
  const data: unknown = text ? JSON.parse(text) : null
  if (!resp.ok) {
    const detail =
      data && typeof data === 'object' && 'detail' in data
        ? String((data as { detail: unknown }).detail)
        : resp.statusText
    throw new ApiError(resp.status, detail)
  }
  return data as T
}

async function requestBlob(path: string): Promise<Blob> {
  const headers = new Headers({ Accept: 'application/json, text/csv' })
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const resp = await fetch(`/api/v1${path}`, { headers })
  if (!resp.ok) {
    const data: unknown = await resp.json().catch(() => null)
    const detail =
      data && typeof data === 'object' && 'detail' in data
        ? String((data as { detail: unknown }).detail)
        : resp.statusText
    throw new ApiError(resp.status, detail)
  }
  return resp.blob()
}

function qs(params: Record<string, string | number | boolean | undefined | null>): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') search.set(key, String(value))
  }
  const out = search.toString()
  return out ? `?${out}` : ''
}

export const api = {
  getOverviewSummary(): Promise<OverviewSummary> {
    return request('/discovery/overview')
  },
  getTopologyGraph(includeObservedDevices = false): Promise<TopologyGraph> {
    return request(`/topology/physical-graph${qs({ include_clients: includeObservedDevices })}`)
  },
  downloadTopology(format: 'json' | 'csv'): Promise<Blob> {
    return requestBlob(`/topology/export${qs({ format })}`)
  },
  createNetworkLink(input: NetworkLinkInput): Promise<NetworkLink> {
    return request('/links', { method: 'POST', body: JSON.stringify(input) })
  },
  patchNetworkLink(id: number, input: NetworkLinkPatch): Promise<NetworkLink> {
    return request(`/links/${id}`, { method: 'PATCH', body: JSON.stringify(input) })
  },
  listNetworkLinks(params: {
    verification_status?: NetworkLink['verification_status']
    device_id?: number
    limit?: number
    offset?: number
  } = {}): Promise<Page<NetworkLink>> {
    return request(`/links${qs(params)}`)
  },
  listTopologyObservations(params: {
    device_id?: number
    link_id?: number
    limit?: number
    offset?: number
  } = {}): Promise<Page<TopologyObservation>> {
    return request(`/topology-observations${qs(params)}`)
  },
  createTopologyObservation(input: TopologyObservationInput): Promise<TopologyObservation> {
    return request('/topology-observations', { method: 'POST', body: JSON.stringify(input) })
  },
  listDiscoveryRuns(params: { limit?: number; offset?: number } = {}): Promise<Page<DiscoveryRun>> {
    return request(`/discovery/runs${qs(params)}`)
  },
  enqueueDiscoveryRun(): Promise<DiscoveryRun> {
    return request('/discovery/runs', { method: 'POST' })
  },
  inspectDevice(id: number): Promise<HardwareIdentity> {
    return request(`/devices/${id}/inspect`, { method: 'POST' })
  },
  listDiscoveryObservations(
    runId: number,
    params: { limit?: number; offset?: number } = {},
  ): Promise<DiscoveryObservationPage> {
    return request(`/discovery/runs/${runId}/observations${qs(params)}`)
  },
  login(username: string, password: string): Promise<{ access_token: string }> {
    return request('/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) })
  },
  me(): Promise<CurrentUser> {
    return request('/auth/me')
  },
  listDevices(params: {
    q?: string
    online?: boolean
    observation_status?: 'observed' | 'stale' | 'unknown'
    location_id?: number
    model_id?: number
    limit?: number
    offset?: number
  }): Promise<Page<Device>> {
    return request(`/devices${qs(params)}`)
  },
  getDevice(id: number): Promise<Device> {
    return request(`/devices/${id}`)
  },
  createDevice(input: DeviceInput): Promise<Device> {
    return request('/devices', { method: 'POST', body: JSON.stringify(input) })
  },
  patchDevice(id: number, input: Partial<DeviceInput>): Promise<Device> {
    return request(`/devices/${id}`, { method: 'PATCH', body: JSON.stringify(input) })
  },
  deleteDevice(id: number): Promise<void> {
    return request(`/devices/${id}`, { method: 'DELETE' })
  },
  listInterfaces(deviceId: number): Promise<DeviceInterface[]> {
    return request(`/devices/${deviceId}/interfaces`)
  },
  listAddresses(deviceId: number): Promise<DeviceAddress[]> {
    return request(`/devices/${deviceId}/addresses`)
  },
  listLocations(params: { kind?: string; q?: string } = {}): Promise<Location[]> {
    return request(`/locations${qs(params)}`)
  },
  createLocation(input: LocationInput): Promise<Location> {
    return request('/locations', { method: 'POST', body: JSON.stringify(input) })
  },
  deleteLocation(id: number): Promise<void> {
    return request(`/locations/${id}`, { method: 'DELETE' })
  },
  listModels(params: { q?: string } = {}): Promise<Page<DeviceModel>> {
    return request(`/device-models${qs(params)}`)
  },
  listAuditEvents(params: {
    actor?: string
    action?: string
    limit?: number
    offset?: number
  } = {}): Promise<Page<AuditEvent>> {
    return request(`/audit-events${qs(params)}`)
  },
}
