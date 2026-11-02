import { useCallback, useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { api } from '../lib/api'
import type { Location } from '../lib/types'

const LOCATION_KINDS = ['country', 'site', 'building', 'floor', 'room', 'rack', 'zone', 'other']

interface TreeItem {
  location: Location
  children: TreeItem[]
}

function buildTree(locations: Location[]): TreeItem[] {
  const byId = new Map<number, TreeItem>()
  for (const location of locations) byId.set(location.id, { location, children: [] })
  const roots: TreeItem[] = []
  for (const item of byId.values()) {
    const parentId = item.location.parent_id
    const parent = parentId != null ? byId.get(parentId) : undefined
    if (parent) parent.children.push(item)
    else roots.push(item)
  }
  return roots
}

function TreeRow({
  item,
  depth,
  onDelete,
}: {
  item: TreeItem
  depth: number
  onDelete: (location: Location) => void
}) {
  return (
    <>
      <tr className="border-b border-slate-800 hover:bg-slate-900/60">
        <td className="py-2 pr-4" style={{ paddingLeft: depth * 1.25 + 'rem' }}>
          <span className="text-slate-200">{item.location.name}</span>
          {item.location.code && <span className="ml-2 text-xs text-slate-500">{item.location.code}</span>}
        </td>
        <td className="py-2 pr-4 text-slate-300">{item.location.kind}</td>
        <td className="py-2 text-right">
          <button
            type="button"
            onClick={() => onDelete(item.location)}
            className="rounded border border-slate-700 px-2 py-0.5 text-xs text-slate-400 hover:border-red-800 hover:text-red-300"
          >
            Delete
          </button>
        </td>
      </tr>
      {item.children.map((child) => (
        <TreeRow key={child.location.id} item={child} depth={depth + 1} onDelete={onDelete} />
      ))}
    </>
  )
}

export default function Locations() {
  const [locations, setLocations] = useState<Location[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    api
      .listLocations()
      .then(setLocations)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : 'Failed to load'))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    const form = new FormData(event.currentTarget)
    const parentId = form.get('parent_id')
    try {
      await api.createLocation({
        kind: String(form.get('kind')),
        name: String(form.get('name')).trim(),
        parent_id: parentId ? Number(parentId) : null,
        code: String(form.get('code') ?? '').trim() || null,
      })
      event.currentTarget.reset()
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Create failed')
    }
  }

  async function handleDelete(location: Location) {
    setError(null)
    if (!window.confirm(`Delete ${location.kind} "${location.name}"?`)) return
    try {
      await api.deleteLocation(location.id)
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete failed')
    }
  }

  const tree = locations ? buildTree(locations) : []

  return (
    <div>
      <h1 className="mb-4 text-xl font-semibold text-white">Locations</h1>

      {error && (
        <p className="mb-3 rounded border border-red-900 bg-red-950/50 px-3 py-2 text-sm text-red-300">
          {error}
        </p>
      )}

      <form
        onSubmit={handleCreate}
        className="mb-6 grid grid-cols-1 gap-3 rounded-lg border border-slate-800 bg-slate-900 p-4 sm:grid-cols-4"
      >
        <label className="text-sm text-slate-300">
          Kind *
          <select name="kind" defaultValue="building" className="field">
            {LOCATION_KINDS.map((kind) => (
              <option key={kind} value={kind}>
                {kind}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm text-slate-300">
          Name *
          <input name="name" required className="field" />
        </label>
        <label className="text-sm text-slate-300">
          Code
          <input name="code" placeholder="e.g. B2" className="field" />
        </label>
        <label className="text-sm text-slate-300">
          Parent
          <select name="parent_id" defaultValue="" className="field">
            <option value="">— root —</option>
            {(locations ?? []).map((loc) => (
              <option key={loc.id} value={loc.id}>
                {loc.kind}: {loc.name}
              </option>
            ))}
          </select>
        </label>
        <div className="sm:col-span-4">
          <button
            type="submit"
            className="rounded bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-500"
          >
            Create location
          </button>
        </div>
      </form>

      {!locations ? (
        <p className="text-slate-400">Loading…</p>
      ) : (
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b border-slate-700 text-left text-slate-400">
              <th className="py-2 pr-4">Name</th>
              <th className="py-2 pr-4">Kind</th>
              <th className="py-2 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {tree.map((item) => (
              <TreeRow key={item.location.id} item={item} depth={0} onDelete={handleDelete} />
            ))}
            {locations.length === 0 && (
              <tr>
                <td colSpan={3} className="py-4 text-slate-500">
                  No locations yet — create the first one above.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  )
}
