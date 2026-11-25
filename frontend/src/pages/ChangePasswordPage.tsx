import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError } from '@/lib/api'
import { useAuth } from '@/context/AuthContext'
import { Button } from '@/components/ui/button'

/** Forced password change (D-14) and voluntary password change.
 * POST /api/auth/change-password/ — the backend requires the current
 * password and enforces the policy (Django defaults, minimum length 10).
 * A successful change clears must_change_password and keeps the session. */
export default function ChangePasswordPage() {
  const { changePassword } = useAuth()
  const navigate = useNavigate()
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    if (newPassword !== confirmPassword) {
      setError('New passwords do not match.')
      return
    }
    setPending(true)
    try {
      await changePassword(currentPassword, newPassword)
      navigate('/')
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.detail
          : 'Password change failed. Try again.',
      )
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="mx-auto max-w-sm">
      <h1 className="text-2xl font-semibold">Change your password</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Your account requires a new password before you can continue. It
        must be at least 10 characters.
      </p>
      <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4">
        <label className="flex flex-col gap-1 text-sm font-medium">
          Current password
          <input
            type="password"
            autoComplete="current-password"
            required
            value={currentPassword}
            onChange={(event) => setCurrentPassword(event.target.value)}
            className="h-9 rounded-md border border-input bg-background px-3 text-sm outline-none focus-visible:ring-1 focus-visible:ring-ring"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium">
          New password
          <input
            type="password"
            autoComplete="new-password"
            required
            value={newPassword}
            onChange={(event) => setNewPassword(event.target.value)}
            className="h-9 rounded-md border border-input bg-background px-3 text-sm outline-none focus-visible:ring-1 focus-visible:ring-ring"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium">
          Confirm new password
          <input
            type="password"
            autoComplete="new-password"
            required
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            className="h-9 rounded-md border border-input bg-background px-3 text-sm outline-none focus-visible:ring-1 focus-visible:ring-ring"
          />
        </label>
        {error && (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}
        <Button type="submit" disabled={pending}>
          {pending ? 'Changing password…' : 'Change password'}
        </Button>
      </form>
    </div>
  )
}
