import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import Layout from '@/components/Layout'

// The auth context hits /api/auth/session/ on mount; the layout smoke
// test only needs the shell to render, so the session call is stubbed.
vi.mock('@/context/AuthContext', async (importOriginal) => {
  const original = await importOriginal<typeof import('@/context/AuthContext')>()
  return {
    ...original,
    useAuth: () => ({
      user: null,
      loading: false,
      login: vi.fn(),
      logout: vi.fn(),
      changePassword: vi.fn(),
    }),
  }
})

describe('Layout', () => {
  it('renders the header, navigation and page shell', () => {
    render(
      <MemoryRouter>
        <Layout />
      </MemoryRouter>,
    )
    expect(screen.getByRole('link', { name: 'MediCore' })).toBeInTheDocument()
    expect(screen.getByRole('navigation', { name: 'Main' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Dashboard' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Sign in' })).toBeInTheDocument()
  })
})
