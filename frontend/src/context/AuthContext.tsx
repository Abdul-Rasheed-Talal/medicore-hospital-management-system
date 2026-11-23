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
}

interface AuthContextValue {
  user: SessionUser | null
  loading: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
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

  const login = useCallback(async (username: string, password: string) => {
    await ensureCsrf()
    const sessionUser = await api<SessionUser>('/api/auth/login/', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    })
    setUser(sessionUser)
  }, [])

  const logout = useCallback(async () => {
    await api('/api/auth/logout/', { method: 'POST' })
    setUser(null)
  }, [])

  const value = useMemo(
    () => ({ user, loading, login, logout }),
    [user, loading, login, logout],
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside <AuthProvider>')
  return context
}
