import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import { AuthProvider } from './lib/auth'
import { useAuth } from './lib/auth-context'
import AuditLog from './pages/AuditLog'
import DeviceDetail from './pages/DeviceDetail'
import Devices from './pages/Devices'
import Discovery from './pages/Discovery'
import Locations from './pages/Locations'
import Login from './pages/Login'
import Overview from './pages/Overview'
import Topology from './pages/Topology'
import type { ReactNode } from 'react'

function RequireAuth({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) return <p className="p-6 text-slate-400">Loading…</p>
  if (!user) return <Navigate to="/login" replace />
  return children
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            element={
              <RequireAuth>
                <Layout />
              </RequireAuth>
            }
          >
            <Route index element={<Overview />} />
            <Route path="topology" element={<Topology />} />
            <Route path="devices" element={<Devices />} />
            <Route path="discovery" element={<Discovery />} />
            <Route path="devices/:id" element={<DeviceDetail />} />
            <Route path="locations" element={<Locations />} />
            <Route path="audit" element={<AuditLog />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
