import { useCallback, useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import type { Device, DeviceModel, Location, Page } from '../lib/types'

const DEVICE_TYPES = ['router', 'switch', 'ap', 'server', 'endpoint', 'other']
const CONDITIONS = ['good', 'fair', 'poor', 'maintenance', 'retired']
const CONFIDENCES = ['mac', 'lldp', 'snmp', 'radius', 'manual']

export default function Devices() {
  const [page, setPage] = useState<Page<Device> | null>(null)
  const [locations, setLocations] = useState<Location[]>([])
  const [models, setModels] = useState<DeviceModel[]>([])
  const [search, setSearch] = useState('')
  const [locationFilter, setLocationFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState<'' | 'observed' | 'stale' | 'unknown'>('')
  const [error, setError] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)

  const load = useCallback(() => {
    api
      .listDevices({
        q: search || undefined,
        location_id: locationFilter ? Number(locationFilter) : undefined,
        observation_status: statusFilter || undefined,
        limit: 100,
      })
      .then(setPage)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : 'Failed to load'))
  }, [search, locationFilter, statusFilter])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    Promise.all([api.listLocations(), api.listModels()])
      .then(([locationList, modelPage]) => {
        setLocations(locationList)
        setModels(modelPage.items)
      })
      .catch(() => {})
  }, [])

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    const form = new FormData(event.currentTarget)
    const value = (name: string) => String(form.get(name) ?? '').trim()
    try {
      await api.createDevice({
        mac_address: value('mac_address'),
        label: value('label') || null,
        vendor: value('vendor') || null,
        type: value('type'),
        ip_address: value('ip_address') || null,
        hostname: value('hostname') || null,
        model_id: form.get('model_id') ? Number(form.get('model_id')) : null,
        location_id: form.get('location_id') ? Number(form.get('location_id')) : null,
        serial_number: value('serial_number') || null,
        role: value('role') || null,
        condition: value('condition'),
        identity_confidence: value('identity_confidence'),
      })
      setShowForm(false)
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Create failed')
    }
  }

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold text-white">Devices</h1>
        <button
          type="button"
          onClick={() => setShowForm((v) => !v)}
          className="rounded bg-sky-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-sky-500"
        >
          {showForm ? 'Cancel' : 'Add device'}
        </button>
      </div>

      {error && (
        <p className="mb-3 rounded border border-red-900 bg-red-950/50 px-3 py-2 text-sm text-red-300">
          {error}
        </p>
      )}

      {showForm && (
        <form
          onSubmit={handleCreate}
          className="mb-6 grid grid-cols-1 gap-3 rounded-lg border border-slate-800 bg-slate-900 p-4 sm:grid-cols-3"
        >
          <label className="text-sm text-slate-300">
            MAC address *
            <input
              name="mac_address"
              required
              placeholder="6c:3b:6b:xx:xx:xx"
              className="field"
            />
          </label>
          <label className="text-sm text-slate-300">
            Label
            <input name="label" className="field" />
          </label>
          <label className="text-sm text-slate-300">
            Vendor
            <input name="vendor" className="field" />
          </label>
          <label className="text-sm text-slate-300">
            Type
            <select name="type" defaultValue="switch" className="field">
              {DEVICE_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm text-slate-300">
            IP address
            <input name="ip_address" placeholder="10.x.x.x" className="field" />
          </label>
          <label className="text-sm text-slate-300">
            Hostname
            <input name="hostname" className="field" />
          </label>
          <label className="text-sm text-slate-300">
            Location
            <select name="location_id" defaultValue="" className="field">
              <option value="">—</option>
              {locations.map((loc) => (
                <option key={loc.id} value={loc.id}>
                  {loc.kind}: {loc.name}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm text-slate-300">
            Model
            <select name="model_id" defaultValue="" className="field">
              <option value="">—</option>
              {models.map((model) => (
                <option key={model.id} value={model.id}>
                  {model.vendor} {model.model}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm text-slate-300">
            Serial number
            <input name="serial_number" className="field" />
          </label>
          <label className="text-sm text-slate-300">
            Role
            <input name="role" placeholder="distribution / access / …" className="field" />
          </label>
          <label className="text-sm text-slate-300">
            Condition
            <select name="condition" defaultValue="good" className="field">
              {CONDITIONS.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm text-slate-300">
            Identity confidence
            <select name="identity_confidence" defaultValue="manual" className="field">
              {CONFIDENCES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </label>
          <div className="sm:col-span-3">
            <button
              type="submit"
              className="rounded bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-500"
            >
              Create device
            </button>
          </div>
        </form>
      )}

      <div className="mb-4 flex flex-wrap gap-3">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search MAC, label, IP, hostname…"
          className="w-64 rounded border border-slate-700 bg-slate-950 px-3 py-1.5 text-sm text-white focus:border-sky-500 focus:outline-none"
        />
        <select
          value={locationFilter}
          onChange={(e) => setLocationFilter(e.target.value)}
          className="rounded border border-slate-700 bg-slate-950 px-3 py-1.5 text-sm text-white"
        >
          <option value="">All locations</option>
          {locations.map((loc) => (
            <option key={loc.id} value={loc.id}>
              {loc.kind}: {loc.name}
            </option>
          ))}
        </select>
        <select
          value={statusFilter}
          onChange={(e) =>
            setStatusFilter(e.target.value as '' | 'observed' | 'stale' | 'unknown')
          }
          className="rounded border border-slate-700 bg-slate-950 px-3 py-1.5 text-sm text-white"
        >
          <option value="">Any status</option>
          <option value="observed">Recently observed</option>
          <option value="stale">Stale observation</option>
          <option value="unknown">Unknown</option>
        </select>
      </div>

      {!page ? (
        <p className="text-slate-400">Loading…</p>
      ) : (
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b border-slate-700 text-left text-slate-400">
              <th className="py-2 pr-4">Status</th>
              <th className="py-2 pr-4">MAC</th>
              <th className="py-2 pr-4">Label</th>
              <th className="py-2 pr-4">Type</th>
              <th className="py-2 pr-4">IP</th>
              <th className="py-2 pr-4">Location</th>
              <th className="py-2 pr-4">Model</th>
              <th className="py-2">Condition</th>
            </tr>
          </thead>
          <tbody>
            {page.items.map((device) => (
              <tr key={device.id} className="border-b border-slate-800 hover:bg-slate-900/60">
                <td className="py-2 pr-4">
                  <span
                    className={`inline-block h-2 w-2 rounded-full ${
                      device.observation_status === 'observed'
                        ? 'bg-emerald-400'
                        : device.observation_status === 'stale'
                          ? 'bg-amber-400'
                          : 'bg-slate-600'
                    }`}
                    title={device.observation_status}
                  />
                </td>
                <td className="py-2 pr-4 font-mono text-xs text-slate-300">{device.mac_address}</td>
                <td className="py-2 pr-4">
                  <Link to={`/devices/${device.id}`} className="text-sky-400 hover:underline">
                    {device.label || device.hostname || '—'}
                  </Link>
                </td>
                <td className="py-2 pr-4 text-slate-300">{device.type}</td>
                <td className="py-2 pr-4 font-mono text-xs text-slate-300">{device.ip_address ?? '—'}</td>
                <td className="py-2 pr-4 text-slate-300">{device.location?.name ?? '—'}</td>
                <td className="py-2 pr-4 text-slate-300">
                  {device.model ? `${device.model.vendor} ${device.model.model}` : '—'}
                </td>
                <td className="py-2 text-slate-300">{device.condition}</td>
              </tr>
            ))}
            {page.items.length === 0 && (
              <tr>
                <td colSpan={8} className="py-4 text-slate-500">
                  No devices match the current filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      )}
      {page && (
        <p className="mt-3 text-xs text-slate-500">
          Showing {page.items.length} of {page.total} devices
        </p>
      )}
    </div>
  )
}
