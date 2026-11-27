import { Link, Outlet, useNavigate } from 'react-router-dom'
import { LogOut } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { Button } from '@/components/ui/button'

/** Shared page shell: header with navigation, then the page content. */
export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  async function handleLogout() {
    await logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
          <Link to="/" className="text-lg font-semibold tracking-tight">
            MediCore
          </Link>
          <nav aria-label="Main" className="flex items-center gap-1">
            <Button variant="ghost" size="sm" asChild>
              <Link to="/">Dashboard</Link>
            </Button>
            {user && (
              <Button variant="ghost" size="sm" asChild>
                <Link to="/setup/departments">Hospital setup</Link>
              </Button>
            )}
            {user ? (
              <>
                <span className="px-2 text-sm text-muted-foreground">
                  {user.username} · {user.role}
                </span>
                <Button variant="ghost" size="sm" asChild>
                  <Link to="/change-password">Change password</Link>
                </Button>
                <Button variant="ghost" size="sm" onClick={handleLogout}>
                  <LogOut aria-hidden />
                  Sign out
                </Button>
              </>
            ) : (
              <Button variant="ghost" size="sm" asChild>
                <Link to="/login">Sign in</Link>
              </Button>
            )}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}
