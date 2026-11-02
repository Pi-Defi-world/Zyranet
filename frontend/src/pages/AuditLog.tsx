import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import type { AuditEvent, Page } from '../lib/types'

const OUTCOME_CLASS: Record<string, string> = {
  success: 'text-emerald-300',
  denied: 'text-amber-300',
  error: 'text-red-300',
}

export default function AuditLog() {
  const [page, setPage] = useState<Page<AuditEvent> | null>(null)
  const [actor, setActor] = useState('')
  const [action, setAction] = useState('')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .listAuditEvents({ actor: actor || undefined, action: action || undefined, limit: 100 })
      .then(setPage)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : 'Failed to load'))
  }, [actor, action])

  return (
    <div>
      <h1 className="mb-4 text-xl font-semibold text-white">Audit log</h1>

      {error && <p className="mb-3 text-sm text-red-400">{error}</p>}

      <div className="mb-4 flex flex-wrap gap-3">
        <input
          value={actor}
          onChange={(e) => setActor(e.target.value)}
          placeholder="Filter by actor…"
          className="w-48 rounded border border-slate-700 bg-slate-950 px-3 py-1.5 text-sm text-white focus:border-sky-500 focus:outline-none"
        />
        <input
          value={action}
          onChange={(e) => setAction(e.target.value)}
          placeholder="Filter by action (prefix)…"
          className="w-64 rounded border border-slate-700 bg-slate-950 px-3 py-1.5 text-sm text-white focus:border-sky-500 focus:outline-none"
        />
      </div>

      {!page ? (
        <p className="text-slate-400">Loading…</p>
      ) : (
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b border-slate-700 text-left text-slate-400">
              <th className="py-2 pr-4">Time</th>
              <th className="py-2 pr-4">Actor</th>
              <th className="py-2 pr-4">Action</th>
              <th className="py-2 pr-4">Entity</th>
              <th className="py-2 pr-4">Outcome</th>
              <th className="py-2">Detail</th>
            </tr>
          </thead>
          <tbody>
            {page.items.map((event) => (
              <tr key={event.id} className="border-b border-slate-800 align-top">
                <td className="py-2 pr-4 whitespace-nowrap text-slate-400">
                  {new Date(event.created_at).toLocaleString()}
                </td>
                <td className="py-2 pr-4 text-slate-200">{event.actor}</td>
                <td className="py-2 pr-4 text-slate-300">{event.action}</td>
                <td className="py-2 pr-4 text-slate-300">
                  {event.entity_type ? `${event.entity_type} ${event.entity_id ?? ''}` : '—'}
                </td>
                <td className={`py-2 pr-4 ${OUTCOME_CLASS[event.outcome] ?? 'text-slate-300'}`}>
                  {event.outcome}
                </td>
                <td className="py-2 font-mono text-xs text-slate-500">
                  {Object.keys(event.detail ?? {}).length > 0 ? JSON.stringify(event.detail) : '—'}
                </td>
              </tr>
            ))}
            {page.items.length === 0 && (
              <tr>
                <td colSpan={6} className="py-4 text-slate-500">
                  No audit events match.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      )}
      {page && <p className="mt-3 text-xs text-slate-500">Showing {page.items.length} of {page.total}</p>}
    </div>
  )
}
