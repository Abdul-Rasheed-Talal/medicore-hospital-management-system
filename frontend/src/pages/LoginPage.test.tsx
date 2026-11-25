import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import LoginPage from '@/pages/LoginPage'
import type { SessionUser } from '@/context/AuthContext'

const normalUser: SessionUser = {
  id: 1,
  username: 'doctor1',
  first_name: 'Doctor',
  last_name: 'One',
  role: 'Doctor',
  must_change_password: false,
}

const forcedUser: SessionUser = {
  ...normalUser,
  username: 'reception1',
  role: 'Receptionist',
  must_change_password: true,
}

const loginMock = vi.fn()

vi.mock('@/context/AuthContext', async (importOriginal) => {
  const original =
    await importOriginal<typeof import('@/context/AuthContext')>()
  return {
    ...original,
    useAuth: () => ({
      user: null,
      loading: false,
      login: loginMock,
      logout: vi.fn(),
      changePassword: vi.fn(),
    }),
  }
})

function renderLogin() {
  return render(
    <MemoryRouter initialEntries={['/login']}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<div>Dashboard page</div>} />
        <Route
          path="/change-password"
          element={<div>Change password page</div>}
        />
      </Routes>
    </MemoryRouter>,
  )
}

describe('LoginPage', () => {
  beforeEach(() => {
    loginMock.mockReset()
  })

  it('accepts a username or an email and signs in with the identifier field', async () => {
    loginMock.mockResolvedValue(normalUser)
    const user = userEvent.setup()
    renderLogin()
    await user.type(
      screen.getByLabelText(/username or email/i),
      'doctor1@example.com',
    )
    await user.type(screen.getByLabelText(/^password$/i), 'correct-password')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))
    await waitFor(() =>
      expect(screen.getByText('Dashboard page')).toBeInTheDocument(),
    )
    expect(loginMock).toHaveBeenCalledWith(
      'doctor1@example.com',
      'correct-password',
    )
  })

  it('sends a forced-password-change user to the change-password screen', async () => {
    loginMock.mockResolvedValue(forcedUser)
    const user = userEvent.setup()
    renderLogin()
    await user.type(screen.getByLabelText(/username or email/i), 'reception1')
    await user.type(screen.getByLabelText(/^password$/i), 'temporary-password')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))
    await waitFor(() =>
      expect(screen.getByText('Change password page')).toBeInTheDocument(),
    )
  })

  it('shows the backend error when sign-in fails', async () => {
    const { ApiError } = await import('@/lib/api')
    loginMock.mockRejectedValue(new ApiError(400, 'Invalid username or password.'))
    const user = userEvent.setup()
    renderLogin()
    await user.type(screen.getByLabelText(/username or email/i), 'doctor1')
    await user.type(screen.getByLabelText(/^password$/i), 'wrong-password')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))
    await waitFor(() =>
      expect(
        screen.getByText('Invalid username or password.'),
      ).toBeInTheDocument(),
    )
    expect(screen.queryByText('Dashboard page')).not.toBeInTheDocument()
  })
})
