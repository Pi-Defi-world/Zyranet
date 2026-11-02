import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../lib/api'
import { useAuth } from '../lib/auth-context'
import type { Device, DeviceAddress, DeviceInterface, HardwareIdentity, NetworkLink } from '../lib/types'

export default function DeviceDetail() {
  const { user } = useAuth()
  const { id } = useParams()
  const deviceId = Number(id)
  const [device, setDevice] = useState<Device | null>(null)
  const [interfaces, setInterfaces] = useState<DeviceInterface[]>([])
  const [addresses, setAddresses] = useState<DeviceAddress[]>([])
  const [links, setLinks] = useState<NetworkLink[]>([])
  const [error, setError] = useState<string | null>(null)
  const [inspection, setInspection] = useState<HardwareIdentity | null>(null)
  const [inspectionError, setInspectionError] = useState<string | null>(null)
  const [inspecting, setInspecting] = useState(false)

  function inspect() {
    setInspectionError(null)
    setInspecting(true)
    api.inspectDevice(deviceId)
      .then(setInspection)
      .catch((err: unknown) => setInspectionError(err instanceof Error ? err.message : 'Inspection failed'))
      .finally(() => setInspecting(false))
  }

  const load = useCallback(() => {
    Promise.all([
      api.getDevice(deviceId),
      api.listInterfaces(deviceId),
      api.listAddresses(deviceId),
      api.listNetworkLinks({ device_id: deviceId, limit: 100 }),
    ])
      .then(([dev, ints, addrs, linkPage]) => {
        setDevice(dev)
        setInterfaces(ints)
        setAddresses(addrs)
        setLinks(linkPage.items)
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : 'Failed to load'))
  }, [deviceId])

  useEffect(() => {
    load()
  }, [load])

  if (error) return <p className="text-red-400">{error}</p>
  if (!device) return <p className="text-slate-400">Loading…</p>

  return (
    <div>
      <p className="mb-2 text-sm text-slate-500">
        <Link to="/devices" className="text-sky-400 hover:underline">
          ← Devices
        </Link>
      </p>
      <div className="mb-4 flex items-center gap-3">
        <h1 className="text-xl font-semibold text-white">
          {device.label || device.hostname || device.mac_address}
        </h1>
        <span
          className={`rounded px-2 py-0.5 text-xs ${
            device.observation_status === 'observed'
              ? 'bg-emerald-500/15 text-emerald-300'
              : device.observation_status === 'stale'
                ? 'bg-amber-500/15 text-amber-300'
                : 'bg-slate-800 text-slate-400'
          }`}
        >
          {device.observation_status}
        </span>
      </div>

      <dl className="grid grid-cols-1 gap-x-8 gap-y-2 rounded-lg border border-slate-800 bg-slate-900 p-4 text-sm sm:grid-cols-2 lg:grid-cols-3">
        {[
          ['MAC address', device.mac_address],
          ['Type', device.type],
          ['IP address', device.ip_address ?? '—'],
          ['Vendor', device.vendor ?? '—'],
          ['Serial', device.serial_number ?? '—'],
          ['Hardware revision', device.hardware_revision ?? '—'],
          ['Firmware', device.firmware ?? '—'],
          ['Role', device.role ?? '—'],
          ['Condition', device.condition],
          ['Identity confidence', device.identity_confidence],
          ['Location', device.location ? `${device.location.kind}: ${device.location.name}` : '—'],
          [
            'Model',
            device.model ? `${device.model.vendor} ${device.model.model}` : '—',
          ],
          ['First seen', new Date(device.first_seen).toLocaleString()],
          ['Last seen', new Date(device.last_seen).toLocaleString()],
        ].map(([label, value]) => (
          <div key={label}>
            <dt className="text-xs uppercase tracking-wide text-slate-500">{label}</dt>
            <dd className="text-slate-200">{value}</dd>
          </div>
        ))}
        {device.notes && (
          <div className="sm:col-span-2 lg:col-span-3">
            <dt className="text-xs uppercase tracking-wide text-slate-500">Notes</dt>
            <dd className="text-slate-200">{device.notes}</dd>
          </div>
        )}
      </dl>

      <section className="mt-5 rounded-lg border border-slate-800 bg-slate-900 p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-medium text-slate-200">Read-only hardware inspection</h2>
            <p className="mt-1 text-xs text-slate-500">
              Queries standard SNMP system identity only. It does not change device configuration.
            </p>
          </div>
          {(user?.role === 'operator' || user?.role === 'admin') && (
            <button
              type="button"
              onClick={inspect}
              disabled={inspecting || !device.ip_address}
              className="rounded bg-sky-600 px-3 py-2 text-sm text-white hover:bg-sky-500 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {inspecting ? 'Inspecting…' : 'Inspect via SNMP'}
            </button>
          )}
        </div>
        {inspectionError && <p className="mt-3 text-sm text-red-300">{inspectionError}</p>}
        {inspection && (
          <dl className="mt-4 grid grid-cols-1 gap-3 border-t border-slate-800 pt-4 text-sm sm:grid-cols-2">
            <div><dt className="text-xs uppercase tracking-wide text-slate-500">Reported name</dt><dd className="text-slate-200">{inspection.sys_name ?? 'Not reported'}</dd></div>
            <div><dt className="text-xs uppercase tracking-wide text-slate-500">Object identifier</dt><dd className="break-all font-mono text-slate-200">{inspection.sys_object_id ?? 'Not reported'}</dd></div>
            <div className="sm:col-span-2"><dt className="text-xs uppercase tracking-wide text-slate-500">System description</dt><dd className="break-words text-slate-200">{inspection.sys_descr ?? 'Not reported'}</dd></div>
            <div><dt className="text-xs uppercase tracking-wide text-slate-500">Uptime</dt><dd className="text-slate-200">{inspection.sys_uptime_ticks == null ? 'Not reported' : `${Math.floor(inspection.sys_uptime_ticks / 6000)} minutes`}</dd></div>
            <div><dt className="text-xs uppercase tracking-wide text-slate-500">Adapter / collected</dt><dd className="text-slate-300">{inspection.adapter} · {new Date(inspection.collected_at).toLocaleString()}</dd></div>
          </dl>
        )}
      </section>

      <section className="mt-6">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-sm font-medium text-slate-300">Recorded topology links</h2>
          <Link to="/topology" className="text-xs text-sky-400 hover:underline">Open topology</Link>
        </div>
        {links.length === 0 ? (
          <p className="rounded-lg border border-slate-800 bg-slate-900 p-4 text-sm text-slate-500">
            No link endpoints are recorded for this device.
          </p>
        ) : (
          <div className="space-y-3">
            {links.map((link) => {
              const endpoint = link.endpoints.find((item) => item.device_id === device.id)
              const peer = link.endpoints.find((item) => item.side !== endpoint?.side)
              return (
                <article key={link.id} className="rounded-lg border border-slate-800 bg-slate-900 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <h3 className="text-sm font-medium text-white">{link.label || `Link ${link.id}`}</h3>
                      <p className="mt-1 text-xs text-slate-400">
                        {endpoint?.interface_name || 'Interface unspecified'} → {peer?.device_label || 'Unknown peer'}
                        {peer?.interface_name ? ` · ${peer.interface_name}` : ''}
                      </p>
                    </div>
                    <span className="rounded border border-slate-700 px-2 py-1 text-xs text-slate-300">
                      {link.verification_status}
                    </span>
                  </div>
                  <p className="mt-2 text-xs text-slate-500">
                    {link.medium} · {link.confidence == null ? 'confidence unknown' : `confidence ${link.confidence}`}
                  </p>
                  {(link.verification_evidence || link.notes) && (
                    <p className="mt-2 break-words text-sm text-slate-300">
                      {link.verification_evidence || link.notes}
                    </p>
                  )}
                </article>
              )
            })}
          </div>
        )}
      </section>

      <h2 className="mb-2 mt-6 text-sm font-medium text-slate-300">Interfaces</h2>
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-slate-700 text-left text-slate-400">
            <th className="py-2 pr-4">Name</th>
            <th className="py-2 pr-4">Kind</th>
            <th className="py-2 pr-4">MAC</th>
            <th className="py-2 pr-4">Link</th>
            <th className="py-2">Speed (Mbps)</th>
          </tr>
        </thead>
        <tbody>
          {interfaces.map((iface) => (
            <tr key={iface.id} className="border-b border-slate-800">
              <td className="py-2 pr-4 text-slate-200">{iface.name}</td>
              <td className="py-2 pr-4 text-slate-300">{iface.kind}</td>
              <td className="py-2 pr-4 font-mono text-xs text-slate-300">{iface.mac_address ?? '—'}</td>
              <td className="py-2 pr-4 text-slate-300">{iface.link_state ?? '—'}</td>
              <td className="py-2 text-slate-300">{iface.speed_mbps ?? '—'}</td>
            </tr>
          ))}
          {interfaces.length === 0 && (
            <tr>
              <td colSpan={5} className="py-3 text-slate-500">
                No interfaces recorded.
              </td>
            </tr>
          )}
        </tbody>
      </table>

      <h2 className="mb-2 mt-6 text-sm font-medium text-slate-300">Addresses</h2>
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-slate-700 text-left text-slate-400">
            <th className="py-2 pr-4">Address</th>
            <th className="py-2 pr-4">Prefix</th>
            <th className="py-2 pr-4">Source</th>
            <th className="py-2 pr-4">Current</th>
            <th className="py-2">Last seen</th>
          </tr>
        </thead>
        <tbody>
          {addresses.map((address) => (
            <tr key={address.id} className="border-b border-slate-800">
              <td className="py-2 pr-4 font-mono text-xs text-slate-200">{address.address}</td>
              <td className="py-2 pr-4 text-slate-300">
                {address.prefix_length != null ? `/${address.prefix_length}` : '—'}
              </td>
              <td className="py-2 pr-4 text-slate-300">{address.source}</td>
              <td className="py-2 pr-4 text-slate-300">{address.current ? 'yes' : 'no'}</td>
              <td className="py-2 text-slate-300">{new Date(address.last_seen).toLocaleString()}</td>
            </tr>
          ))}
          {addresses.length === 0 && (
            <tr>
              <td colSpan={5} className="py-3 text-slate-500">
                No addresses recorded.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
