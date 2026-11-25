import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AuthProvider, useAuth, type SessionUser } from '@/context/AuthContext'

const sessionUser: SessionUser = {
  id: 1,
  username: 'reception1',
  first_name: 'Reception',
  last_name: 'One',
  role: 'Receptionist',
  must_change_password: true,
}

function Probe() {
  const { user, loading, login, changePassword } = useAuth()
  return (
    <div>
      <p>{loading ? 'loading' : 'loaded'}</p>
      <p>{user ? `user:${user.username}` : 'no-user'}</p>
      <p>{user ? `must-change:${String(user.must_change_password)}` : ''}</p>
      <button
        onClick={() =>
          login('reception1', 'temporary-password').catch(() => {})
        }
      >
        sign in
      </button>
      <button
        onClick={() =>
          changePassword('temporary-password', 'new-secure-password').catch(
            () => {},
          )
        }
      >
        change password
      </button>
    </div>
  )
}

describe('AuthContext', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) => {
        if (url.endsWith('/api/auth/session/')) {
          return {
            ok: true,
            status: 200,
            json: async () => sessionUser,
          } as Response
        }
        throw new Error(`unexpected fetch: ${url}`)
      }),
    )
  })

  it('restores the session and keeps the must-change-password flag', async () => {
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    )
    await waitFor(() => expect(screen.getByText('loaded')).toBeInTheDocument())
    expect(screen.getByText('user:reception1')).toBeInTheDocument()
    expect(screen.getByText('must-change:true')).toBeInTheDocument()
  })

  it('login returns the signed-in user including the flag', async () => {
    const fetchMock = vi.fn(async (url: string) => {
      if (url.endsWith('/api/auth/csrf/')) {
        return { ok: true, status: 200, json: async () => ({}) } as Response
      }
      if (url.endsWith('/api/auth/login/')) {
        return {
          ok: true,
          status: 200,
          json: async () => sessionUser,
        } as Response
      }
      if (url.endsWith('/api/auth/session/')) {
        return {
          ok: false,
          status: 403,
          json: async () => ({ detail: 'Not signed in.' }),
        } as Response
      }
      throw new Error(`unexpected fetch: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    )
    await waitFor(() => expect(screen.getByText('loaded')).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: 'sign in' }))
    await waitFor(() =>
      expect(screen.getByText('must-change:true')).toBeInTheDocument(),
    )
    const loginCall = (
      fetchMock.mock.calls as unknown as Array<[string, { body?: unknown }]>
    ).find((call) => String(call[0]).endsWith('/api/auth/login/'))
    expect(loginCall).toBeDefined()
    expect(JSON.parse(String(loginCall?.[1]?.body ?? '{}'))).toEqual({
      identifier: 'reception1',
      password: 'temporary-password',
    })
  })

  it('changePassword posts to the backend and clears the flag', async () => {
    const clearedUser = { ...sessionUser, must_change_password: false }
    const fetchMock = vi.fn(async (url: string) => {
      if (url.endsWith('/api/auth/session/')) {
        return {
          ok: true,
          status: 200,
          json: async () => sessionUser,
        } as Response
      }
      if (url.endsWith('/api/auth/change-password/')) {
        return {
          ok: true,
          status: 200,
          json: async () => clearedUser,
        } as Response
      }
      throw new Error(`unexpected fetch: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    )
    await waitFor(() => expect(screen.getByText('loaded')).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: 'change password' }))
    await waitFor(() =>
      expect(screen.getByText('must-change:false')).toBeInTheDocument(),
    )
    const changeCall = (
      fetchMock.mock.calls as unknown as Array<[string, { body?: unknown }]>
    ).find((call) => String(call[0]).endsWith('/api/auth/change-password/'))
    expect(JSON.parse(String(changeCall?.[1]?.body ?? '{}'))).toEqual({
      current_password: 'temporary-password',
      new_password: 'new-secure-password',
    })
  })
})
