import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError } from '@/lib/api'
import { useAuth } from '@/context/AuthContext'
import { Button } from '@/components/ui/button'

/** Sign-in page shell. Calls the backend session auth
 * (POST /api/auth/login/) — no patient UI yet. */
export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setPending(true)
    try {
      await login(username, password)
      navigate('/')
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Sign-in failed. Try again.')
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="mx-auto max-w-sm">
      <h1 className="text-2xl font-semibold">Sign in to MediCore</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Staff sign-in. Accounts are created by an administrator.
      </p>
      <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4">
        <label className="flex flex-col gap-1 text-sm font-medium">
          Username
          <input
            type="text"
            autoComplete="username"
            required
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            className="h-9 rounded-md border border-input bg-background px-3 text-sm outline-none focus-visible:ring-1 focus-visible:ring-ring"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium">
          Password
          <input
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="h-9 rounded-md border border-input bg-background px-3 text-sm outline-none focus-visible:ring-1 focus-visible:ring-ring"
          />
        </label>
        {error && (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}
        <Button type="submit" disabled={pending}>
          {pending ? 'Signing in…' : 'Sign in'}
        </Button>
      </form>
    </div>
  )
}
