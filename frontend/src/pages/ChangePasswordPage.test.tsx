import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import ChangePasswordPage from '@/pages/ChangePasswordPage'

const changePasswordMock = vi.fn()

vi.mock('@/context/AuthContext', async (importOriginal) => {
  const original =
    await importOriginal<typeof import('@/context/AuthContext')>()
  return {
    ...original,
    useAuth: () => ({
      user: {
        id: 1,
        username: 'reception1',
        first_name: 'Reception',
        last_name: 'One',
        role: 'Receptionist',
        must_change_password: true,
      },
      loading: false,
      login: vi.fn(),
      logout: vi.fn(),
      changePassword: changePasswordMock,
    }),
  }
})

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/change-password']}>
      <Routes>
        <Route path="/change-password" element={<ChangePasswordPage />} />
        <Route path="/" element={<div>Dashboard page</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('ChangePasswordPage', () => {
  beforeEach(() => {
    changePasswordMock.mockReset()
  })

  it('refuses mismatched new passwords without calling the backend', async () => {
    const user = userEvent.setup()
    renderPage()
    await user.type(
      screen.getByLabelText(/current password/i),
      'temporary-password',
    )
    await user.type(screen.getByLabelText(/^new password$/i), 'new-secure-one')
    await user.type(
      screen.getByLabelText(/confirm new password/i),
      'new-secure-two',
    )
    await user.click(
      screen.getByRole('button', { name: 'Change password' }),
    )
    await waitFor(() =>
      expect(
        screen.getByText('New passwords do not match.'),
      ).toBeInTheDocument(),
    )
    expect(changePasswordMock).not.toHaveBeenCalled()
  })

  it('changes the password and returns to the dashboard', async () => {
    changePasswordMock.mockResolvedValue(undefined)
    const user = userEvent.setup()
    renderPage()
    await user.type(
      screen.getByLabelText(/current password/i),
      'temporary-password',
    )
    await user.type(
      screen.getByLabelText(/^new password$/i),
      'new-secure-password',
    )
    await user.type(
      screen.getByLabelText(/confirm new password/i),
      'new-secure-password',
    )
    await user.click(
      screen.getByRole('button', { name: 'Change password' }),
    )
    await waitFor(() =>
      expect(screen.getByText('Dashboard page')).toBeInTheDocument(),
    )
    expect(changePasswordMock).toHaveBeenCalledWith(
      'temporary-password',
      'new-secure-password',
    )
  })

  it('shows the backend error when the current password is wrong', async () => {
    const { ApiError } = await import('@/lib/api')
    changePasswordMock.mockRejectedValue(
      new ApiError(400, 'Your current password is incorrect.'),
    )
    const user = userEvent.setup()
    renderPage()
    await user.type(
      screen.getByLabelText(/current password/i),
      'wrong-password',
    )
    await user.type(
      screen.getByLabelText(/^new password$/i),
      'new-secure-password',
    )
    await user.type(
      screen.getByLabelText(/confirm new password/i),
      'new-secure-password',
    )
    await user.click(
      screen.getByRole('button', { name: 'Change password' }),
    )
    await waitFor(() =>
      expect(
        screen.getByText('Your current password is incorrect.'),
      ).toBeInTheDocument(),
    )
    expect(screen.queryByText('Dashboard page')).not.toBeInTheDocument()
  })
})
