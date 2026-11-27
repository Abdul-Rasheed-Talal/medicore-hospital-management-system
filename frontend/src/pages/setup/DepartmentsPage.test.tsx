import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import DepartmentsPage from '@/pages/setup/DepartmentsPage'
import { ApiError } from '@/lib/api'
import type { SessionUser } from '@/context/AuthContext'
import {
  createDepartment,
  deleteDepartment,
  listDepartments,
  updateDepartment,
} from '@/lib/organization'

const adminUser: SessionUser = {
  id: 1,
  username: 'admin',
  first_name: 'Admin',
  last_name: '',
  role: 'admin',
  must_change_password: false,
}

const doctorUser: SessionUser = {
  ...adminUser,
  id: 2,
  username: 'doctor1',
  role: 'doctor',
}

let currentUser: SessionUser | null = adminUser

vi.mock('@/context/AuthContext', async (importOriginal) => {
  const original =
    await importOriginal<typeof import('@/context/AuthContext')>()
  return {
    ...original,
    useAuth: () => ({
      user: currentUser,
      loading: false,
      login: vi.fn(),
      logout: vi.fn(),
      changePassword: vi.fn(),
    }),
  }
})

vi.mock('@/lib/organization', () => ({
  listDepartments: vi.fn(),
  createDepartment: vi.fn(),
  updateDepartment: vi.fn(),
  deleteDepartment: vi.fn(),
}))

const departmentsPage = {
  count: 2,
  next: null,
  previous: null,
  results: [
    {
      id: 1,
      name: 'Outpatient',
      code: 'OPD',
      description: 'General outpatient care',
      is_active: true,
      created_by: 'admin',
      created_at: '2026-11-26T00:00:00Z',
      updated_at: '2026-11-26T00:00:00Z',
    },
    {
      id: 2,
      name: 'Laboratory',
      code: 'LAB',
      description: '',
      is_active: false,
      created_by: 'admin',
      created_at: '2026-11-26T00:00:00Z',
      updated_at: '2026-11-26T00:00:00Z',
    },
  ],
}

function renderPage() {
  return render(
    <MemoryRouter>
      <DepartmentsPage />
    </MemoryRouter>,
  )
}

describe('DepartmentsPage', () => {
  beforeEach(() => {
    currentUser = adminUser
    vi.mocked(listDepartments).mockReset().mockResolvedValue(departmentsPage)
    vi.mocked(createDepartment).mockReset()
    vi.mocked(updateDepartment).mockReset()
    vi.mocked(deleteDepartment).mockReset()
  })

  it('renders the department list', async () => {
    renderPage()
    expect(await screen.findByText('Outpatient')).toBeInTheDocument()
    expect(screen.getByText('OPD')).toBeInTheDocument()
    expect(screen.getByText('Laboratory')).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: 'Inactive' })).toBeInTheDocument()
  })

  it('hides all mutation controls from non-Admin roles', async () => {
    currentUser = doctorUser
    renderPage()
    expect(await screen.findByText('Outpatient')).toBeInTheDocument()
    expect(screen.queryByText('New department')).not.toBeInTheDocument()
    expect(screen.queryByText('Edit')).not.toBeInTheDocument()
    expect(screen.queryByText('Delete')).not.toBeInTheDocument()
  })

  it('shows the backend field error when the code already exists', async () => {
    const user = userEvent.setup()
    vi.mocked(createDepartment).mockRejectedValue(
      new ApiError(400, 'code: A department with this code already exists.', {
        code: ['A department with this code already exists.'],
      }),
    )
    renderPage()
    await user.click(await screen.findByText('New department'))
    await user.type(screen.getByLabelText('Name'), 'Outpatient')
    await user.type(screen.getByLabelText('Code'), 'OPD')
    await user.click(screen.getByRole('button', { name: 'Create department' }))
    await waitFor(() =>
      expect(
        screen.getByText('A department with this code already exists.'),
      ).toBeInTheDocument(),
    )
    expect(createDepartment).toHaveBeenCalledWith({
      name: 'Outpatient',
      code: 'OPD',
      description: '',
    })
  })

  it('shows the deactivation warning when staff remain in the department', async () => {
    const user = userEvent.setup()
    vi.mocked(updateDepartment).mockResolvedValue({
      ...departmentsPage.results[0],
      is_active: false,
      warning:
        'This department still has 2 active staff member(s). They keep their department link.',
    })
    renderPage()
    await user.click((await screen.findAllByText('Deactivate'))[0])
    await waitFor(() =>
      expect(
        screen.getByText(/still has 2 active staff member/),
      ).toBeInTheDocument(),
    )
  })

  it('shows the refusal message when a referenced department cannot be deleted', async () => {
    const user = userEvent.setup()
    vi.mocked(deleteDepartment).mockRejectedValue(
      new ApiError(
        400,
        'Cannot delete this department: it is still linked to 2 staff profile(s). Deactivate it instead.',
      ),
    )
    renderPage()
    await user.click((await screen.findAllByText('Delete'))[0])
    await user.click(await screen.findByText('Confirm delete'))
    await waitFor(() =>
      expect(
        screen.getByText(/still linked to 2 staff profile/),
      ).toBeInTheDocument(),
    )
    expect(deleteDepartment).toHaveBeenCalledWith(1)
  })
})
