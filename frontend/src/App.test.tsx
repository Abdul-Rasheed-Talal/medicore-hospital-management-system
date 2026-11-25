import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import App from '@/App'
import type { SessionUser } from '@/context/AuthContext'

let mockAuth: {
  user: SessionUser | null
  loading: boolean
} = { user: null, loading: false }

vi.mock('@/context/AuthContext', async (importOriginal) => {
  const original =
    await importOriginal<typeof import('@/context/AuthContext')>()
  return {
    ...original,
    AuthProvider: ({ children }: { children: React.ReactNode }) => (
      <>{children}</>
    ),
    useAuth: () => ({
      user: mockAuth.user,
      loading: mockAuth.loading,
      login: vi.fn(),
      logout: vi.fn(),
      changePassword: vi.fn(),
    }),
  }
})

const signedIn: SessionUser = {
  id: 1,
  username: 'doctor1',
  first_name: 'Doctor',
  last_name: 'One',
  role: 'Doctor',
  must_change_password: false,
}

function renderApp(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  )
}

describe('App routes', () => {
  beforeEach(() => {
    mockAuth = { user: null, loading: false }
  })

  it('redirects an unsigned-in visitor from the dashboard to sign-in', () => {
    renderApp('/')
    expect(
      screen.getByRole('heading', { name: 'Sign in to MediCore' }),
    ).toBeInTheDocument()
  })

  it('shows the dashboard to a signed-in user', () => {
    mockAuth = { user: signedIn, loading: false }
    renderApp('/')
    expect(
      screen.getByRole('heading', { name: /Welcome, Doctor/ }),
    ).toBeInTheDocument()
  })

  it('redirects a forced-password-change user to the change-password screen', () => {
    mockAuth = {
      user: { ...signedIn, must_change_password: true },
      loading: false,
    }
    renderApp('/')
    expect(
      screen.getByRole('heading', { name: 'Change your password' }),
    ).toBeInTheDocument()
  })

  it('sends a signed-in user visiting sign-in back to the dashboard', () => {
    mockAuth = { user: signedIn, loading: false }
    renderApp('/login')
    expect(
      screen.getByRole('heading', { name: /Welcome, Doctor/ }),
    ).toBeInTheDocument()
  })

  it('redirects an unsigned-in visitor from change-password to sign-in', () => {
    renderApp('/change-password')
    expect(
      screen.getByRole('heading', { name: 'Sign in to MediCore' }),
    ).toBeInTheDocument()
  })
})
