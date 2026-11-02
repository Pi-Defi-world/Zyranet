import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../lib/auth-context'

const navItems = [
  { to: '/', label: 'Overview', end: true },
  { to: '/topology', label: 'Topology' },
  { to: '/devices', label: 'Devices' },
  { to: '/discovery', label: 'Discovery' },
  { to: '/locations', label: 'Locations' },
  { to: '/audit', label: 'Audit log' },
]

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <div className="flex min-h-full">
      <aside className="flex w-56 flex-col border-r border-slate-800 bg-slate-900 p-4">
        <div className="mb-6">
          <span className="text-lg font-semibold tracking-tight text-sky-400">Zyranet</span>
          <p className="text-xs text-slate-400">Campus network management</p>
        </div>
        <nav className="flex flex-1 flex-col gap-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `rounded px-3 py-2 text-sm ${
                  isActive
                    ? 'bg-sky-500/15 font-medium text-sky-300'
                    : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-slate-800 pt-3">
          <p className="truncate text-sm text-slate-200">{user?.username}</p>
          <p className="text-xs text-slate-500">{user?.role}</p>
          <button
            type="button"
            onClick={handleLogout}
            className="mt-2 w-full rounded border border-slate-700 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-800"
          >
            Sign out
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-x-auto p-6">
        <Outlet />
      </main>
    </div>
  )
}
