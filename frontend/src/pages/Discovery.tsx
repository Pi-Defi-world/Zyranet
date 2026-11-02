import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import { useAuth } from '../lib/auth-context'
import type { DiscoveryObservationPage, DiscoveryRun, Page } from '../lib/types'

const STATUS_STYLE: Record<string, string> = {
  queued: 'text-sky-300',
  succeeded: 'text-emerald-300',
  partial: 'text-amber-300',
  failed: 'text-red-300',
  running: 'text-sky-300',
}

function formatDuration(run: DiscoveryRun): string {
  if (run.status === 'queued') return 'queued'
  if (!run.completed_at) return 'in progress'
  if (!run.started_at) return '—'
  const elapsed = Date.parse(run.completed_at) - Date.parse(run.started_at)
  return Number.isFinite(elapsed) ? `${Math.max(0, elapsed / 1000).toFixed(1)}s` : '—'
}

export default function Discovery() {
  const { user } = useAuth()
  const [runs, setRuns] = useState<Page<DiscoveryRun> | null>(null)
  const [selected, setSelected] = useState<DiscoveryRun | null>(null)
  const [observations, setObservations] = useState<DiscoveryObservationPage | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [queueing, setQueueing] = useState(false)

  function refreshRuns() {
    return api.listDiscoveryRuns({ limit: 50 }).then((page) => {
      setRuns(page)
      if (selected) {
        const refreshed = page.items.find((run) => run.id === selected.id)
        if (refreshed) setSelected(refreshed)
      }
      return page
    })
  }

  function queueScan() {
    setQueueing(true)
    setError(null)
    api.enqueueDiscoveryRun()
      .then((run) => {
        setObservations(null)
        setSelected(run)
        return api.listDiscoveryRuns({ limit: 50 }).then(setRuns)
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : 'Failed to queue scan'))
      .finally(() => setQueueing(false))
  }

  useEffect(() => {
    api.listDiscoveryRuns({ limit: 50 })
      .then((page) => {
        setRuns(page)
        if (page.items[0]) setSelected(page.items[0])
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : 'Failed to load runs'))
  }, [])

  const selectedRunId = selected?.id

  useEffect(() => {
    if (!selectedRunId) return
    let active = true
    api.listDiscoveryObservations(selectedRunId, { limit: 100 })
      .then((page) => { if (active) setObservations(page) })
      .catch((err: unknown) => {
        if (active) setError(err instanceof Error ? err.message : 'Failed to load evidence')
      })
    return () => { active = false }
  }, [selectedRunId])

  useEffect(() => {
    if (!selected || (selected.status !== 'queued' && selected.status !== 'running')) return
    const timer = window.setInterval(() => {
      api.listDiscoveryRuns({ limit: 50 }).then((page) => {
        setRuns(page)
        const refreshed = page.items.find((run) => run.id === selected.id)
        if (refreshed) setSelected(refreshed)
      }).catch(() => undefined)
    }, 3000)
    return () => window.clearInterval(timer)
  }, [selected])

  return (
    <div>
      <h1 className="mb-2 text-xl font-semibold text-white">Discovery</h1>
      {error && <p className="mb-3 text-sm text-red-400">{error}</p>}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        {(user?.role === 'operator' || user?.role === 'admin') && (
          <button
            type="button"
            onClick={queueScan}
            disabled={queueing || runs?.items.some((run) => run.status === 'queued' || run.status === 'running')}
            className="rounded bg-sky-600 px-3 py-2 text-sm font-medium text-white hover:bg-sky-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {queueing ? 'Queueing…' : 'Queue read-only scan'}
          </button>
        )}
        <button
          type="button"
          onClick={() => void refreshRuns().catch((err: unknown) => setError(err instanceof Error ? err.message : 'Failed to refresh'))}
          className="rounded border border-slate-700 px-3 py-2 text-sm text-slate-300 hover:bg-slate-800"
        >
          Refresh runs
        </button>
        {selected?.requested_by && <span className="text-xs text-slate-500">Requested by {selected.requested_by}</span>}
      </div>
      <p className="mb-5 max-w-3xl text-sm text-slate-400">
        Bounded, read-only network observations. A probe reply and a neighbor-table entry are evidence
        of reachability at a point in time; they do not establish device health or Wi-Fi association.
      </p>
      {!runs ? <p className="text-slate-400">Loading runs…</p> : runs.items.length === 0 ? (
        <div className="rounded-lg border border-slate-800 bg-slate-900 p-5 text-sm text-slate-400">
          No discovery runs have been recorded. The discovery worker may not be enabled or configured.
        </div>
      ) : (
        <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
          <section className="overflow-hidden rounded-lg border border-slate-800 bg-slate-900">
            <h2 className="border-b border-slate-800 px-4 py-3 text-sm font-medium text-slate-200">
              Recent runs <span className="text-slate-500">({runs.total})</span>
            </h2>
            <div className="divide-y divide-slate-800">
              {runs.items.map((run) => (
                <button
                  key={run.id}
                  type="button"
                  onClick={() => {
                    setObservations(null)
                    setError(null)
                    setSelected(run)
                  }}
                  className={`w-full px-4 py-3 text-left hover:bg-slate-800/70 ${selected?.id === run.id ? 'bg-slate-800/60' : ''}`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <span className={`text-sm font-medium ${STATUS_STYLE[run.status] ?? 'text-slate-300'}`}>{run.status}</span>
                    <span className="text-xs text-slate-500">{formatDuration(run)}</span>
                  </div>
                  <p className="mt-1 text-xs text-slate-400">{new Date(run.created_at).toLocaleString()}</p>
                  <p className="mt-1 text-xs text-slate-500">
                    {run.devices_observed} devices · {run.probes_responded}/{run.targets_total} replies · {run.probe_errors} errors
                  </p>
                </button>
              ))}
            </div>
          </section>

          <section className="min-w-0 rounded-lg border border-slate-800 bg-slate-900">
            {!selected ? <p className="p-4 text-sm text-slate-500">Select a run.</p> : <>
              <div className="border-b border-slate-800 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h2 className="text-sm font-medium text-white">Run #{selected.id}</h2>
                  <span className={`text-sm ${STATUS_STYLE[selected.status] ?? 'text-slate-300'}`}>{selected.status}</span>
                </div>
                <p className="mt-1 text-xs text-slate-500">
                  Created {new Date(selected.created_at).toLocaleString()}
                  {selected.started_at && ` · Started ${new Date(selected.started_at).toLocaleString()}`}
                </p>
                <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-xs text-slate-400">
                  <span>{selected.targets_total} targets</span><span>{selected.probes_responded} replies</span>
                  <span>{selected.devices_observed} neighbor entries</span><span>{selected.probe_errors} errors</span>
                </div>
                <div className="mt-3 flex flex-wrap gap-1">
                  {selected.scope.map((cidr) => <code key={cidr} className="rounded bg-slate-800 px-2 py-1 text-xs text-sky-200">{cidr}</code>)}
                  {selected.scope.length === 0 && <span className="text-xs text-slate-500">No scan scope recorded</span>}
                </div>
                {selected.error && <p className="mt-3 break-words text-xs text-red-300">{selected.error}</p>}
              </div>
              <div className="overflow-x-auto">
                {!observations ? <p className="p-4 text-sm text-slate-500">Loading evidence…</p> : <>
                  <p className="px-4 py-3 text-xs text-slate-500">
                    {observations.total} sampled sightings are linked to this run. Sampling limits write volume, so this is not a complete record of every device seen.
                  </p>
                  <table className="w-full text-left text-xs">
                    <thead className="text-slate-500"><tr className="border-y border-slate-800">
                      <th className="px-4 py-2">Seen</th><th className="px-4 py-2">Device</th><th className="px-4 py-2">Address</th><th className="px-4 py-2">Source / evidence</th>
                    </tr></thead>
                    <tbody>{observations.items.map((item) => <tr key={item.id} className="border-b border-slate-800 align-top">
                      <td className="whitespace-nowrap px-4 py-2 text-slate-400">{new Date(item.seen_at).toLocaleTimeString()}</td>
                      <td className="px-4 py-2"><Link className="text-sky-300 hover:underline" to={`/devices/${item.device_id}`}>{item.label || item.vendor || item.mac_address}</Link><div className="mt-0.5 font-mono text-slate-500">{item.mac_address}</div></td>
                      <td className="px-4 py-2 font-mono text-slate-300">{item.ip_address || '—'}</td>
                      <td className="max-w-xs break-words px-4 py-2 text-slate-400"><span>{item.source}</span><pre className="mt-1 whitespace-pre-wrap font-mono text-[10px] text-slate-500">{JSON.stringify(item.evidence)}</pre></td>
                    </tr>)}
                    {observations.items.length === 0 && <tr><td colSpan={4} className="px-4 py-5 text-center text-slate-500">No sampled sightings linked to this run.</td></tr>}
                    </tbody>
                  </table>
                </>}
              </div>
            </>}
          </section>
        </div>
      )}
    </div>
  )
}
