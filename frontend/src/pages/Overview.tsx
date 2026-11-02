import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import type { AuditEvent, OverviewSummary } from '../lib/types'

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-white">{value}</p>
    </div>
  )
}

export default function Overview() {
  const [summary, setSummary] = useState<OverviewSummary | null>(null)
  const [events, setEvents] = useState<AuditEvent[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([
      api.getOverviewSummary(),
      api.listAuditEvents({ limit: 8 }),
    ])
      .then(([summaryData, auditPage]) => {
        setSummary(summaryData)
        setEvents(auditPage.items)
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : 'Failed to load'))
  }, [])

  if (error) return <p className="text-red-400">{error}</p>
  if (!summary || !events) return <p className="text-slate-400">Loading…</p>

  return (
    <div>
      <h1 className="mb-4 text-xl font-semibold text-white">Overview</h1>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <StatCard label="Inventory" value={summary.devices} />
        <StatCard label="Recently observed" value={summary.observed_devices} />
        <StatCard label="Stale observation" value={summary.stale_devices} />
        <StatCard label="Unknown status" value={summary.unknown_devices} />
        <StatCard label="Locations" value={summary.locations} />
      </div>

      <section className="mt-6 rounded-lg border border-slate-800 bg-slate-900 p-4">
        <h2 className="text-sm font-medium text-slate-300">Latest discovery run</h2>
        {summary.latest_discovery ? (
          <div className="mt-2 flex flex-wrap items-center gap-x-5 gap-y-2 text-sm">
            <span className="text-white">{summary.latest_discovery.status}</span>
            <span className="text-slate-400">
              {summary.latest_discovery.devices_observed} neighbour entries observed
            </span>
            <span className="text-slate-400">
              {summary.latest_discovery.probes_responded}/{summary.latest_discovery.targets_total} probes replied
            </span>
            <span className="text-xs text-slate-500">
              {summary.latest_discovery.started_at
                ? `Started ${new Date(summary.latest_discovery.started_at).toLocaleString()}`
                : `Created ${new Date(summary.latest_discovery.created_at).toLocaleString()}`}
            </span>
          </div>
        ) : (
          <p className="mt-2 text-sm text-slate-500">No discovery run has been recorded.</p>
        )}
        <p className="mt-3 text-xs text-slate-500">
          “Recently observed” means seen within the configured freshness window. Neighbour-table
          discovery does not confirm Wi-Fi association or device health.
        </p>
      </section>

      <h2 className="mb-2 mt-8 text-sm font-medium text-slate-300">Recent activity</h2>
      <div className="rounded-lg border border-slate-800 bg-slate-900">
        {events.length === 0 && <p className="p-4 text-sm text-slate-500">No audit events yet.</p>}
        {events.map((event) => (
          <div
            key={event.id}
            className="flex items-center justify-between border-b border-slate-800 px-4 py-2 text-sm last:border-none"
          >
            <span className="text-slate-200">
              <span className="font-medium">{event.actor}</span> {event.action}
              {event.entity_type ? ` → ${event.entity_type} ${event.entity_id ?? ''}` : ''}
            </span>
            <span className="text-xs text-slate-500">{new Date(event.created_at).toLocaleString()}</span>
          </div>
        ))}
      </div>

      <p className="mt-6 text-sm text-slate-500">
        Review the <Link className="text-sky-400 hover:underline" to="/topology">topology</Link>, manage{' '}
        <Link className="text-sky-400 hover:underline" to="/devices"> devices</Link>, or update{' '}
        <Link className="text-sky-400 hover:underline" to="/locations">locations</Link>.
      </p>
    </div>
  )
}
