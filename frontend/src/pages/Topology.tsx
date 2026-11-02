import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import { useAuth } from '../lib/auth-context'
import type {
  Device,
  DeviceInterface,
  NetworkLinkInput,
  TopologyGraph,
  TopologyNode,
  TopologyObservation,
} from '../lib/types'

const WIDTH = 1100
const HEIGHT = 680
const NODE_WIDTH = 188
const NODE_HEIGHT = 78

function valueText(value: unknown): string | null {
  if (typeof value === 'string' || typeof value === 'number') return String(value)
  return null
}

function detailText(value: unknown): string | null {
  const scalar = valueText(value)
  if (scalar !== null) return scalar
  if (value && typeof value === 'object') return JSON.stringify(value)
  return null
}

function kindLabel(kind: string): string {
  return kind.replaceAll('_', ' ').toUpperCase()
}

function createPositions(nodes: TopologyNode[]): Map<string, { x: number; y: number }> {
  const points = nodes.map((node, index) => ({
    id: node.id,
    x: typeof node.x === 'number' && Number.isFinite(node.x) ? node.x : (index % 4) * 220,
    y: typeof node.y === 'number' && Number.isFinite(node.y) ? node.y : Math.floor(index / 4) * 170,
  }))
  if (points.length === 0) return new Map()

  const minX = Math.min(...points.map((point) => point.x))
  const maxX = Math.max(...points.map((point) => point.x))
  const minY = Math.min(...points.map((point) => point.y))
  const maxY = Math.max(...points.map((point) => point.y))
  const spanX = Math.max(1, maxX - minX)
  const spanY = Math.max(1, maxY - minY)
  const scale = Math.min((WIDTH - 280) / spanX, (HEIGHT - 220) / spanY)

  return new Map(points.map((point) => [
    point.id,
    {
      x: WIDTH / 2 + (point.x - (minX + maxX) / 2) * scale,
      y: HEIGHT / 2 + (point.y - (minY + maxY) / 2) * scale,
    },
  ]))
}

export default function Topology() {
  const { user } = useAuth()
  const [graph, setGraph] = useState<TopologyGraph | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null)
  const [showObserved, setShowObserved] = useState(false)
  const [observationRefreshKey, setObservationRefreshKey] = useState(0)
  const [showLinkForm, setShowLinkForm] = useState(false)
  const [devices, setDevices] = useState<Device[]>([])
  const [deviceA, setDeviceA] = useState('')
  const [deviceB, setDeviceB] = useState('')
  const [interfacesA, setInterfacesA] = useState<DeviceInterface[]>([])
  const [interfacesB, setInterfacesB] = useState<DeviceInterface[]>([])
  const [observations, setObservations] = useState<TopologyObservation[]>([])
  const [observationError, setObservationError] = useState<string | null>(null)
  const [observationLoading, setObservationLoading] = useState(false)
  const [exporting, setExporting] = useState<'json' | 'csv' | null>(null)
  const [exportError, setExportError] = useState<string | null>(null)
  const [createError, setCreateError] = useState<string | null>(null)
  const [updateError, setUpdateError] = useState<string | null>(null)
  const [observationCreateError, setObservationCreateError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [updatingLink, setUpdatingLink] = useState(false)
  const [savingObservation, setSavingObservation] = useState(false)
  const canEdit = user?.role === 'operator' || user?.role === 'admin'
  const [refreshKey, setRefreshKey] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    api.getTopologyGraph(showObserved)
      .then((data) => {
        if (!active) return
        setGraph(data)
        setSelectedId((current) =>
          current && data.nodes.some((node) => node.id === current) ? current : data.nodes[0]?.id ?? null,
        )
        setSelectedEdgeId((current) =>
          current && data.edges.some((edge) => edge.id === current) ? current : null,
        )
      })
      .catch((err: unknown) => {
        if (active) setError(err instanceof Error ? err.message : 'Could not load topology')
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [showObserved, refreshKey])

  const positions = useMemo(() => createPositions(graph?.nodes ?? []), [graph?.nodes])
  const selected = graph?.nodes.find((node) => node.id === selectedId) ?? null
  const selectedEdge = graph?.edges.find((edge) => edge.id === selectedEdgeId) ?? null
  const selectedMeta = selected?.meta ?? {}
  const zoneLabels = new Map((graph?.zones ?? []).map((zone) => [zone.id, zone.label]))
  const zoneColors = new Map((graph?.zones ?? []).map((zone) => [zone.id, zone.color]))
  const selectedLinkId = selectedEdge ? Number(selectedEdge.meta?.link_id) : 0

  function refreshGraph(refreshSelectedObservations = true) {
    setLoading(true)
    setError(null)
    setRefreshKey((value) => value + 1)
    if (refreshSelectedObservations && selectedLinkId) {
      setObservations([])
      setObservationLoading(true)
      setObservationError(null)
    } else if (!refreshSelectedObservations) {
      setObservations([])
      setObservationLoading(false)
      setObservationError(null)
    }
  }

  function selectEdge(edgeId: string) {
    setSelectedEdgeId(edgeId)
    setSelectedId(null)
    setObservations([])
    setObservationLoading(true)
    setObservationError(null)
    setObservationCreateError(null)
    setObservationRefreshKey((value) => value + 1)
  }

  function selectNode(nodeId: string) {
    setSelectedId(nodeId)
    setSelectedEdgeId(null)
    setObservations([])
    setObservationLoading(false)
  }

  useEffect(() => {
    if (!selectedLinkId) return
    let active = true
    api.listTopologyObservations({ link_id: selectedLinkId, limit: 20 })
      .then((page) => { if (active) setObservations(page.items) })
      .catch((err: unknown) => {
        if (active) setObservationError(err instanceof Error ? err.message : 'Could not load evidence history')
      })
      .finally(() => { if (active) setObservationLoading(false) })
    return () => { active = false }
  }, [selectedLinkId, refreshKey, observationRefreshKey])

  useEffect(() => {
    if (!showLinkForm) return
    let active = true
    api.listDevices({ limit: 500 })
      .then((page) => {
        if (!active) return
        const networkTypes = new Set([
          'router', 'switch', 'ap', 'server', 'radio', 'gateway', 'firewall', 'modem',
          'access_point', 'controller', 'repeater', 'ont',
        ])
        setDevices(page.items.filter((device) => device.role || networkTypes.has(device.type)))
      })
      .catch((err: unknown) => {
        if (active) setCreateError(err instanceof Error ? err.message : 'Could not load devices')
      })
    return () => { active = false }
  }, [showLinkForm])

  useEffect(() => {
    let active = true
    const deviceId = Number(deviceA)
    if (!deviceId) return
    api.listInterfaces(deviceId)
      .then((items) => { if (active) setInterfacesA(items) })
      .catch(() => { if (active) setInterfacesA([]) })
    return () => { active = false }
  }, [deviceA])

  useEffect(() => {
    let active = true
    const deviceId = Number(deviceB)
    if (!deviceId) return
    api.listInterfaces(deviceId)
      .then((items) => { if (active) setInterfacesB(items) })
      .catch(() => { if (active) setInterfacesB([]) })
    return () => { active = false }
  }, [deviceB])

  async function handleCreateLink(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setCreateError(null)
    setSaving(true)
    const form = new FormData(event.currentTarget)
    const value = (name: string) => String(form.get(name) ?? '').trim()
    const confidenceText = value('confidence')
    const payload: NetworkLinkInput = {
      label: value('label') || null,
      link_type: value('link_type') as NetworkLinkInput['link_type'],
      medium: value('medium') as NetworkLinkInput['medium'],
      verification_status: value('verification_status') as NetworkLinkInput['verification_status'],
      confidence: confidenceText ? Number(confidenceText) : null,
      source: 'manual',
      verification_evidence: value('verification_evidence') || null,
      notes: value('notes'),
      endpoints: [
        {
          side: 'A',
          device_id: Number(value('device_a')),
          interface_id: value('interface_a') ? Number(value('interface_a')) : null,
        },
        {
          side: 'B',
          device_id: Number(value('device_b')),
          interface_id: value('interface_b') ? Number(value('interface_b')) : null,
        },
      ],
    }
    try {
      await api.createNetworkLink(payload)
      setShowLinkForm(false)
      setSelectedEdgeId(null)
      setDeviceA('')
      setDeviceB('')
      refreshGraph(false)
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : 'Could not record link')
    } finally {
      setSaving(false)
    }
  }

  async function handleUpdateLink(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedEdge) return
    setUpdateError(null)
    setUpdatingLink(true)
    const form = new FormData(event.currentTarget)
    const value = (name: string) => String(form.get(name) ?? '').trim()
    const confidenceText = value('confidence')
    try {
      await api.patchNetworkLink(Number(selectedEdge.meta?.link_id), {
        verification_status: value('verification_status') as NetworkLinkInput['verification_status'],
        confidence: confidenceText ? Number(confidenceText) : null,
        verification_evidence: value('verification_evidence') || null,
      })
      refreshGraph()
    } catch (err) {
      setUpdateError(err instanceof Error ? err.message : 'Could not update link')
    } finally {
      setUpdatingLink(false)
    }
  }

  async function handleCreateObservation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedEdge) return
    setObservationCreateError(null)
    setSavingObservation(true)
    const element = event.currentTarget
    const form = new FormData(element)
    const value = (name: string) => String(form.get(name) ?? '').trim()
    const note = value('observation_note')
    const confidenceText = value('observation_confidence')
    try {
      await api.createTopologyObservation({
        link_id: Number(selectedEdge.meta?.link_id),
        source: 'manual',
        verification_status: value('observation_status') as TopologyObservation['verification_status'],
        confidence: confidenceText ? Number(confidenceText) : null,
        evidence: { note },
        notes: note,
      })
      element.reset()
      setObservations([])
      setObservationLoading(true)
      setObservationRefreshKey((current) => current + 1)
    } catch (err) {
      setObservationCreateError(err instanceof Error ? err.message : 'Could not save evidence')
    } finally {
      setSavingObservation(false)
    }
  }

  async function handleExport(format: 'json' | 'csv') {
    setExportError(null)
    setExporting(format)
    try {
      const blob = await api.downloadTopology(format)
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = `zyranet-topology.${format}`
      document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
      window.setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch (err) {
      setExportError(err instanceof Error ? err.message : 'Could not export topology')
    } finally {
      setExporting(null)
    }
  }

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-white">Campus topology</h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-400">
            Hardware inventory and evidence-backed links. This graph uses device IDs and interface IDs;
            it does not turn scan sightings or the legacy planning map into physical connections.
          </p>
        </div>
        <div className="flex gap-2">
          {canEdit && (
            <button
              type="button"
              onClick={() => { setCreateError(null); setShowLinkForm((value) => !value) }}
              className="rounded bg-sky-600 px-3 py-2 text-sm font-medium text-white hover:bg-sky-500"
            >
              {showLinkForm ? 'Cancel' : 'Record link'}
            </button>
          )}
          <button
            type="button"
            onClick={() => handleExport('json')}
            disabled={exporting !== null}
            className="rounded border border-slate-700 px-3 py-2 text-sm text-slate-300 hover:bg-slate-800 disabled:opacity-50"
          >
            {exporting === 'json' ? 'Exporting…' : 'Export JSON'}
          </button>
          <button
            type="button"
            onClick={() => handleExport('csv')}
            disabled={exporting !== null}
            className="rounded border border-slate-700 px-3 py-2 text-sm text-slate-300 hover:bg-slate-800 disabled:opacity-50"
          >
            {exporting === 'csv' ? 'Exporting…' : 'Export CSV'}
          </button>
          <button
            type="button"
            onClick={() => refreshGraph()}
            disabled={loading}
            className="rounded border border-slate-700 px-3 py-2 text-sm text-slate-300 hover:bg-slate-800 disabled:opacity-50"
          >
            {loading ? 'Loading…' : 'Refresh'}
          </button>
        </div>
      </div>

      {exportError && <p className="mb-4 text-sm text-red-300">{exportError}</p>}

      <div className="mb-4 rounded-lg border border-amber-800/70 bg-amber-950/30 px-4 py-3 text-sm text-amber-100">
        Records marked reported, observed, or associated are shown with dashed links. Only links marked
        verified after recording operator evidence are drawn as solid connections. Device and interface
        inventory still requires field confirmation.
      </div>

      {showLinkForm && (
        <form
          onSubmit={handleCreateLink}
          className="mb-4 grid gap-3 rounded-lg border border-slate-800 bg-slate-900 p-4 lg:grid-cols-4"
        >
          <label className="text-sm text-slate-300">
            Link label
            <input name="label" maxLength={120} placeholder="e.g. Library switch uplink" className="mt-1 w-full rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white" />
          </label>
          <label className="text-sm text-slate-300">
            Link type
            <select name="link_type" className="mt-1 w-full rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white">
              <option value="physical">Physical</option><option value="logical">Logical</option><option value="wan">WAN</option>
            </select>
          </label>
          <label className="text-sm text-slate-300">
            Medium
            <select name="medium" className="mt-1 w-full rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white">
              <option value="unknown">Unknown</option><option value="ethernet">Ethernet</option><option value="fiber">Fiber</option><option value="wireless">Wireless</option><option value="wan">WAN</option><option value="logical">Logical</option><option value="other">Other</option>
            </select>
          </label>
          <label className="text-sm text-slate-300">
            Evidence status
            <select name="verification_status" className="mt-1 w-full rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white">
              <option value="reported">Reported</option><option value="observed">Observed</option><option value="associated">Associated</option><option value="verified">Verified</option>
            </select>
          </label>
          <label className="text-sm text-slate-300">
            Endpoint A device
            <select name="device_a" required value={deviceA} onChange={(event) => { setDeviceA(event.target.value); setInterfacesA([]) }} className="mt-1 w-full rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white">
              <option value="">Select device</option>
              {devices.map((device) => <option key={device.id} value={device.id}>{device.label || device.hostname || device.mac_address} · #{device.id}</option>)}
            </select>
          </label>
          <label className="text-sm text-slate-300">
            Endpoint A interface
            <select name="interface_a" className="mt-1 w-full rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white">
              <option value="">Unspecified</option>
              {interfacesA.map((iface) => <option key={iface.id} value={iface.id}>{iface.name} · #{iface.id}</option>)}
            </select>
          </label>
          <label className="text-sm text-slate-300">
            Endpoint B device
            <select name="device_b" required value={deviceB} onChange={(event) => { setDeviceB(event.target.value); setInterfacesB([]) }} className="mt-1 w-full rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white">
              <option value="">Select device</option>
              {devices.map((device) => <option key={device.id} value={device.id}>{device.label || device.hostname || device.mac_address} · #{device.id}</option>)}
            </select>
          </label>
          <label className="text-sm text-slate-300">
            Endpoint B interface
            <select name="interface_b" className="mt-1 w-full rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white">
              <option value="">Unspecified</option>
              {interfacesB.map((iface) => <option key={iface.id} value={iface.id}>{iface.name} · #{iface.id}</option>)}
            </select>
          </label>
          <label className="text-sm text-slate-300">
            Confidence (0–1)
            <input name="confidence" type="number" min="0" max="1" step="0.01" className="mt-1 w-full rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white" />
          </label>
          <label className="text-sm text-slate-300 lg:col-span-2">
            Reported basis / notes *
            <textarea name="notes" required maxLength={2000} placeholder="Record how this endpoint relationship is known" className="mt-1 min-h-16 w-full rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white" />
          </label>
          <label className="text-sm text-slate-300 lg:col-span-2">
            Verification evidence (required for verified)
            <input name="verification_evidence" maxLength={2000} placeholder="Inspection, photo, port label, or discovery evidence reference" className="mt-1 w-full rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white" />
          </label>
          <div className="flex items-end">
            <button type="submit" disabled={saving || devices.length < 2} className="rounded bg-emerald-700 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-600 disabled:opacity-50">
              {saving ? 'Saving…' : 'Save link'}
            </button>
          </div>
          <p className="text-xs text-slate-500 lg:col-span-4">
            If a port is not known yet, leave the interface unspecified and record the link as reported. Do not infer endpoints from a device sighting.
          </p>
          {createError && <p className="text-sm text-red-300 lg:col-span-4">{createError}</p>}
        </form>
      )}

      {error && (
        <p className="mb-4 rounded border border-red-900 bg-red-950/50 px-3 py-2 text-sm text-red-300">
          {error}
        </p>
      )}

      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <span className="rounded border border-slate-700 px-2 py-1">
            {graph?.stats.infrastructure_nodes ?? '—'} infrastructure records
          </span>
          <span className="rounded border border-slate-700 px-2 py-1">
            {graph?.stats.links ?? '—'} links shown
          </span>
          {showObserved && (
            <span className="rounded border border-slate-700 px-2 py-1">
              {graph?.stats.observed_devices ?? '—'} observed devices
            </span>
          )}
          {graph?.stats.truncated && (
            <span className="rounded border border-amber-700 px-2 py-1 text-amber-300">
              Showing {graph.stats.infrastructure_nodes} of {graph.stats.total_devices} network devices
            </span>
          )}
        </div>
        <button
          type="button"
          onClick={() => {
            setLoading(true)
            setError(null)
            setShowObserved((value) => !value)
          }}
          className="rounded border border-slate-700 px-3 py-2 text-xs text-slate-300 hover:bg-slate-800"
        >
          {showObserved ? 'Hide observed devices' : 'Show observed devices'}
        </button>
      </div>

      <div className="grid gap-4 2xl:grid-cols-[minmax(0,1fr)_300px]">
        <section className="overflow-auto rounded-lg border border-slate-800 bg-slate-900">
          {loading && !graph ? (
            <p className="p-6 text-sm text-slate-400">Loading topology…</p>
          ) : !graph ? (
            <div className="p-6 text-sm text-slate-400">
              Topology data is unavailable. Refresh the page after the API is reachable.
            </div>
          ) : graph.nodes.length > 0 ? (
            <svg
              aria-label="Campus network topology diagram"
              className="h-[620px] min-w-[900px] w-full"
              viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
              role="group"
            >
              <rect width={WIDTH} height={HEIGHT} fill="#020617" />
              {graph.edges.map((edge) => {
                const from = positions.get(edge.from)
                const to = positions.get(edge.to)
                if (!from || !to) return null
                const medium = valueText(edge.meta?.medium) ?? 'ethernet'
                const isSelected = selectedEdgeId === edge.id
                const stroke = isSelected
                  ? '#f8fafc'
                  : (edge.color?.color
                    ?? (medium === 'wireless' ? '#38bdf8' : medium === 'logical' ? '#a78bfa' : '#64748b'))
                return (
                  <g
                    key={edge.id}
                    role="button"
                    tabIndex={0}
                    aria-label={`Link ${edge.id}, ${valueText(edge.meta?.verification_status) ?? 'unverified'}`}
                    aria-pressed={isSelected}
                    className="cursor-pointer"
                    onClick={() => selectEdge(edge.id)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault()
                        selectEdge(edge.id)
                      }
                    }}
                  >
                    <line
                      x1={from.x}
                      y1={from.y}
                      x2={to.x}
                      y2={to.y}
                      stroke={stroke}
                      strokeWidth={isSelected ? '4' : '2'}
                      strokeDasharray={edge.dashes || medium === 'logical' ? '7 6' : undefined}
                    />
                    {edge.label && (
                      <text
                        x={(from.x + to.x) / 2}
                        y={(from.y + to.y) / 2 - 7}
                        textAnchor="middle"
                        fill="#94a3b8"
                        fontSize="12"
                      >
                        {edge.label}
                      </text>
                    )}
                  </g>
                )
              })}
              {graph.nodes.map((node) => {
                const point = positions.get(node.id)
                if (!point) return null
                const color = zoneColors.get(node.group) ?? '#64748b'
                const isSelected = selectedId === node.id
                const subtitle = valueText(node.meta.subtitle)
                const subtitleLabel = subtitle ? subtitle.slice(0, 24) : ''
                return (
                  <g
                    key={node.id}
                    role="button"
                    tabIndex={0}
                    aria-label={`${node.label}, ${kindLabel(node.kind)}`}
                    aria-pressed={isSelected}
                    onClick={() => selectNode(node.id)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault()
                        selectNode(node.id)
                      }
                    }}
                    className="cursor-pointer"
                  >
                    <title>{node.title}</title>
                    <rect
                      x={point.x - NODE_WIDTH / 2}
                      y={point.y - NODE_HEIGHT / 2}
                      width={NODE_WIDTH}
                      height={NODE_HEIGHT}
                      rx="10"
                      fill="#0f172a"
                      stroke={isSelected ? '#e2e8f0' : color}
                      strokeWidth={isSelected ? '3' : '2'}
                    />
                    <text
                      x={point.x}
                      y={point.y - 8}
                      textAnchor="middle"
                      fill="#f8fafc"
                      fontSize="14"
                      fontWeight="600"
                      textLength={NODE_WIDTH - 22}
                      lengthAdjust="spacingAndGlyphs"
                    >
                      {node.label}
                    </text>
                    <text
                      x={point.x}
                      y={point.y + 14}
                      textAnchor="middle"
                      fill={color}
                      fontSize="10"
                      letterSpacing="1"
                    >
                      {kindLabel(node.kind)}
                      {subtitleLabel ? ` · ${subtitleLabel}` : ''}
                    </text>
                  </g>
                )
              })}
            </svg>
          ) : (
            <div className="p-8">
              <h2 className="font-medium text-white">No topology records yet</h2>
              <p className="mt-2 max-w-xl text-sm text-slate-400">
                Add inventoried equipment with a network role or type before recording physical links.
                Unclassified scan sightings are not treated as infrastructure. Do not infer a connection
                from a device being online or appearing in a scan.
              </p>
              <Link className="mt-4 inline-block text-sm text-sky-400 hover:underline" to="/devices">
                Review device inventory
              </Link>
            </div>
          )}
          {graph?.zones && graph.zones.length > 0 && (
            <div className="flex flex-wrap gap-x-5 gap-y-2 border-t border-slate-800 px-4 py-3">
              {graph.zones.map((zone) => (
                <span key={zone.id} className="flex items-center gap-2 text-xs text-slate-400">
                  <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: zone.color }} />
                  {zone.label}
                </span>
              ))}
            </div>
          )}
          <div className="flex flex-wrap gap-x-5 gap-y-2 border-t border-slate-800 px-4 py-3">
            {[
              ['Reported', '#64748b', true],
              ['Observed', '#38bdf8', true],
              ['Associated', '#fbbf24', true],
              ['Verified', '#34d399', false],
            ].map(([status, color, dashed]) => (
              <span key={String(status)} className="flex items-center gap-2 text-xs text-slate-400">
                <span
                  className={`w-5 border-t-2 ${dashed ? 'border-dashed' : 'border-solid'}`}
                  style={{ borderColor: String(color) }}
                />
                {status}
              </span>
            ))}
          </div>
        </section>

        <aside className="rounded-lg border border-slate-800 bg-slate-900 p-4">
          <h2 className="text-sm font-medium text-slate-200">
            {selectedEdge ? 'Selected link' : 'Selected device'}
          </h2>
          {selectedEdge ? (
            <>
              <p className="mt-3 break-words text-base font-semibold text-white">
                {valueText(selectedEdge.meta?.label) ?? `Link ${valueText(selectedEdge.meta?.link_id) ?? ''}`}
              </p>
              <dl className="mt-4 space-y-3 text-sm">
                {([
                  ['Link ID', selectedEdge.meta?.link_id],
                  ['Status', selectedEdge.meta?.verification_status],
                  ['Type', selectedEdge.meta?.link_type],
                  ['Medium', selectedEdge.meta?.medium],
                  ['Confidence', selectedEdge.meta?.confidence],
                  ['Source', selectedEdge.meta?.source],
                  ['Endpoints', selectedEdge.meta?.endpoints],
                  ['Notes', selectedEdge.meta?.notes],
                  ['Verification evidence', selectedEdge.meta?.verification_evidence],
                  ['Evidence', selectedEdge.meta?.evidence],
                ] as Array<[string, unknown]>).map(([label, value]) => {
                  const rendered = detailText(value)
                  return rendered ? (
                    <div key={String(label)}>
                      <dt className="text-xs text-slate-500">{label}</dt>
                      <dd className="mt-0.5 break-words text-slate-200">{rendered}</dd>
                    </div>
                  ) : null
                })}
              </dl>
              {canEdit && (
                <form key={selectedEdge.id} onSubmit={handleUpdateLink} className="mt-5 border-t border-slate-800 pt-4">
                  <h3 className="mb-3 text-sm font-medium text-slate-200">Update evidence status</h3>
                  <label className="block text-xs text-slate-400">
                    Status
                    <select
                      name="verification_status"
                      defaultValue={String(selectedEdge.meta?.verification_status ?? 'reported')}
                      className="mt-1 w-full rounded border border-slate-700 bg-slate-950 px-2 py-2 text-sm text-white"
                    >
                      <option value="reported">Reported</option>
                      <option value="observed">Observed</option>
                      <option value="associated">Associated</option>
                      <option value="verified">Verified</option>
                    </select>
                  </label>
                  <label className="mt-3 block text-xs text-slate-400">
                    Confidence (0–1)
                    <input
                      name="confidence"
                      type="number"
                      min="0"
                      max="1"
                      step="0.01"
                      defaultValue={valueText(selectedEdge.meta?.confidence) ?? ''}
                      className="mt-1 w-full rounded border border-slate-700 bg-slate-950 px-2 py-2 text-sm text-white"
                    />
                  </label>
                  <label className="mt-3 block text-xs text-slate-400">
                    Verification evidence
                    <textarea
                      name="verification_evidence"
                      maxLength={2000}
                      defaultValue={valueText(selectedEdge.meta?.verification_evidence) ?? ''}
                      className="mt-1 min-h-20 w-full rounded border border-slate-700 bg-slate-950 px-2 py-2 text-sm text-white"
                    />
                  </label>
                  {updateError && <p className="mt-2 text-xs text-red-300">{updateError}</p>}
                  <button type="submit" disabled={updatingLink} className="mt-3 rounded bg-sky-700 px-3 py-2 text-sm text-white hover:bg-sky-600 disabled:opacity-50">
                    {updatingLink ? 'Saving…' : 'Save evidence status'}
                  </button>
                </form>
              )}
              <section className="mt-5 border-t border-slate-800 pt-4">
                <h3 className="text-sm font-medium text-slate-200">Evidence history</h3>
                <p className="mt-1 text-xs text-slate-500">
                  Entries are timestamped and append-only. Update the link status above after reviewing the accumulated evidence.
                </p>
                {observationLoading ? (
                  <p className="mt-2 text-xs text-slate-500">Loading evidence…</p>
                ) : observations.length ? (
                  <ol className="mt-3 space-y-3">
                    {observations.map((observation) => (
                      <li key={observation.id} className="rounded border border-slate-800 bg-slate-950/70 p-3 text-xs">
                        <div className="flex justify-between gap-2 text-slate-300">
                          <span className="font-medium">{kindLabel(observation.verification_status)}</span>
                          <time dateTime={observation.observed_at}>{new Date(observation.observed_at).toLocaleString()}</time>
                        </div>
                        <p className="mt-1 text-slate-500">Source: {observation.source}{observation.confidence !== null ? ` · confidence ${observation.confidence}` : ''}</p>
                        {observation.notes && <p className="mt-2 break-words text-slate-300">{observation.notes}</p>}
                      </li>
                    ))}
                  </ol>
                ) : (
                  <p className="mt-2 text-xs text-slate-500">No append-only evidence has been recorded for this link.</p>
                )}
                {observationError && <p className="mt-2 text-xs text-red-300">{observationError}</p>}
                {canEdit && (
                  <form key={`observation-${selectedEdge.id}`} onSubmit={handleCreateObservation} className="mt-4 space-y-3">
                    <label className="block text-xs text-slate-400">
                      Add evidence entry
                      <select name="observation_status" defaultValue="observed" className="mt-1 w-full rounded border border-slate-700 bg-slate-950 px-2 py-2 text-sm text-white">
                        <option value="reported">Reported</option><option value="observed">Observed</option><option value="associated">Associated</option><option value="verified">Verified</option>
                      </select>
                    </label>
                    <label className="block text-xs text-slate-400">
                      Confidence (0–1)
                      <input name="observation_confidence" type="number" min="0" max="1" step="0.01" className="mt-1 w-full rounded border border-slate-700 bg-slate-950 px-2 py-2 text-sm text-white" />
                    </label>
                    <label className="block text-xs text-slate-400">
                      Field note / evidence reference
                      <textarea name="observation_note" required maxLength={2000} className="mt-1 min-h-16 w-full rounded border border-slate-700 bg-slate-950 px-2 py-2 text-sm text-white" />
                    </label>
                    {observationCreateError && <p className="text-xs text-red-300">{observationCreateError}</p>}
                    <button type="submit" disabled={savingObservation} className="rounded border border-slate-700 px-3 py-2 text-xs text-slate-200 hover:bg-slate-800 disabled:opacity-50">
                      {savingObservation ? 'Saving…' : 'Append evidence'}
                    </button>
                  </form>
                )}
              </section>
            </>
          ) : !selected ? (
            <p className="mt-3 text-sm text-slate-500">Select a node to inspect its stored details.</p>
          ) : (
            <>
              <p className="mt-3 break-words text-base font-semibold text-white">{selected.label}</p>
              <p className="mt-1 text-xs uppercase tracking-wide text-slate-500">
                {kindLabel(selected.kind)} · {zoneLabels.get(selected.group) ?? selected.group}
              </p>
              <dl className="mt-4 space-y-3 text-sm">
                {[
                  ['Condition', valueText(selectedMeta.condition)],
                  ['Identity confidence', valueText(selectedMeta.identity_confidence)],
                  ['IP address', valueText(selectedMeta.ip)],
                  ['MAC address', valueText(selectedMeta.mac)],
                  ['Vendor', valueText(selectedMeta.vendor)],
                  ['Serial number', valueText(selectedMeta.serial_number)],
                  ['Firmware', valueText(selectedMeta.firmware)],
                  ['Location', valueText(selectedMeta.location)],
                  ['Reported source label', valueText(selectedMeta.source_ap)],
                  ['Source', valueText(selectedMeta.source)],
                ].map(([label, value]) =>
                  value ? (
                    <div key={label}>
                      <dt className="text-xs text-slate-500">{label}</dt>
                      <dd className="mt-0.5 break-words text-slate-200">{value}</dd>
                    </div>
                  ) : null,
                )}
              </dl>
              {typeof selectedMeta.device_id === 'number' && (
                <Link
                  to={`/devices/${selectedMeta.device_id}`}
                  className="mt-5 inline-block text-sm text-sky-400 hover:underline"
                >
                  Open device record
                </Link>
              )}
            </>
          )}
          <p className="mt-6 border-t border-slate-800 pt-4 text-xs leading-5 text-slate-500">
            Zyranet records observations and approved topology claims. It does not configure network
            equipment from this view.
          </p>
        </aside>
      </div>
    </div>
  )
}
