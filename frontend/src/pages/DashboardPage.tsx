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
          ? `Signed in as ${user.role}. No modules are available yet — patient registration is the first feature and arrives with Spec 001.`
          : 'Sign in to access MediCore. Staff accounts are created by an administrator.'}
      </p>
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
