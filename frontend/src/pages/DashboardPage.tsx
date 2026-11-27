import { Link } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'

/** Placeholder home page. Feature pages (patients, appointments, …)
 * land with their own approved specs; this page only proves the shell. */
export default function DashboardPage() {
  const { user, loading } = useAuth()

  if (loading) return <p className="text-sm text-muted-foreground">Loading…</p>

  return (
    <div>
      <h1 className="text-2xl font-semibold">
        {user ? `Welcome, ${user.first_name || user.username}` : 'Welcome to MediCore'}
      </h1>
      <p className="mt-2 max-w-prose text-sm text-muted-foreground">
        {user
          ? `Signed in as ${user.role}. Hospital setup is available — departments, staff and services.`
          : 'Sign in to access MediCore. Staff accounts are created by an administrator.'}
      </p>
      {user && (
        <nav aria-label="Modules" className="mt-4">
          <h2 className="text-sm font-semibold">Hospital setup</h2>
          <ul className="mt-1 flex flex-col gap-1 text-sm">
            <li>
              <Link
                to="/setup/departments"
                className="text-primary underline underline-offset-4"
              >
                Departments
              </Link>
            </li>
            <li>
              <Link
                to="/setup/staff"
                className="text-primary underline underline-offset-4"
              >
                Staff directory
              </Link>
            </li>
            <li>
              <Link
                to="/setup/services"
                className="text-primary underline underline-offset-4"
              >
                Services, categories &amp; visit types
              </Link>
            </li>
          </ul>
        </nav>
      )}
      {!user && (
        <p className="mt-4 text-sm">
          <Link to="/login" className="text-primary underline underline-offset-4">
            Sign in
          </Link>
        </p>
      )}
    </div>
  )
}
