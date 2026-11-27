import type { ReactElement } from 'react'
import { Navigate, Outlet, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from '@/context/AuthContext'
import Layout from '@/components/Layout'
import DashboardPage from '@/pages/DashboardPage'
import LoginPage from '@/pages/LoginPage'
import ChangePasswordPage from '@/pages/ChangePasswordPage'
import DepartmentsPage from '@/pages/setup/DepartmentsPage'
import StaffPage from '@/pages/setup/StaffPage'
import ServicesPage from '@/pages/setup/ServicesPage'

function Loading() {
  return <p className="text-sm text-muted-foreground">Loading…</p>
}

/** Signed-in users only. A user forced to change their password (D-14)
 * is sent to the change-password screen instead of any other page. */
function RequireAuth() {
  const { user, loading } = useAuth()
  if (loading) return <Loading />
  if (!user) return <Navigate to="/login" replace />
  if (user.must_change_password) {
    return <Navigate to="/change-password" replace />
  }
  return <Outlet />
}

/** Signed-in users only, including those forced to change their password. */
function RequireSignedIn() {
  const { user, loading } = useAuth()
  if (loading) return <Loading />
  if (!user) return <Navigate to="/login" replace />
  return <Outlet />
}

/** Visitors only: a signed-in user is sent to the dashboard (or to the
 * change-password screen when a change is forced). */
function PublicOnly({ children }: { children: ReactElement }) {
  const { user, loading } = useAuth()
  if (loading) return <Loading />
  if (user) {
    return (
      <Navigate to={user.must_change_password ? '/change-password' : '/'} replace />
    )
  }
  return children
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route element={<Layout />}>
          <Route
            path="login"
            element={
              <PublicOnly>
                <LoginPage />
              </PublicOnly>
            }
          />
          <Route element={<RequireSignedIn />}>
            <Route path="change-password" element={<ChangePasswordPage />} />
          </Route>
          <Route element={<RequireAuth />}>
            <Route index element={<DashboardPage />} />
            <Route path="setup/departments" element={<DepartmentsPage />} />
            <Route path="setup/staff" element={<StaffPage />} />
            <Route path="setup/services" element={<ServicesPage />} />
          </Route>
        </Route>
      </Routes>
    </AuthProvider>
  )
}
