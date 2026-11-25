import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { api, ApiError, ensureCsrf } from '@/lib/api'

export interface SessionUser {
  id: number
  username: string
  first_name: string
  last_name: string
  role: string
  /** Backend flag (D-14): true until the user changes their password. */
  must_change_password: boolean
}

interface AuthContextValue {
  user: SessionUser | null
  loading: boolean
  login: (identifier: string, password: string) => Promise<SessionUser>
  logout: () => Promise<void>
  changePassword: (
    currentPassword: string,
    newPassword: string,
  ) => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<SessionUser | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Restore the session on load: the HttpOnly cookie survives reloads,
    // so a signed-in user stays signed in.
    api<SessionUser>('/api/auth/session/')
      .then(setUser)
      .catch((error: unknown) => {
        if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
          setUser(null)
        }
      })
      .finally(() => setLoading(false))
  }, [])

  const login = useCallback(
    async (identifier: string, password: string) => {
      await ensureCsrf()
      // D-09: the identifier may be a username or an email address.
      const sessionUser = await api<SessionUser>('/api/auth/login/', {
        method: 'POST',
        body: JSON.stringify({ identifier, password }),
      })
      setUser(sessionUser)
      return sessionUser
    },
    [],
  )

  const logout = useCallback(async () => {
    await api('/api/auth/logout/', { method: 'POST' })
    setUser(null)
  }, [])

  const changePassword = useCallback(
    async (currentPassword: string, newPassword: string) => {
      const sessionUser = await api<SessionUser>(
        '/api/auth/change-password/',
        {
          method: 'POST',
          body: JSON.stringify({
            current_password: currentPassword,
            new_password: newPassword,
          }),
        },
      )
      // A successful change clears must_change_password (D-14) and keeps
      // the session alive, so the user continues as the same user.
      setUser(sessionUser)
    },
    [],
  )

  const value = useMemo(
    () => ({ user, loading, login, logout, changePassword }),
    [user, loading, login, logout, changePassword],
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside <AuthProvider>')
  return context
}
