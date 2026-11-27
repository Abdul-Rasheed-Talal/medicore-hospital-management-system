import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import StaffPage from '@/pages/setup/StaffPage'
import { ApiError } from '@/lib/api'
import type { SessionUser } from '@/context/AuthContext'
import {
  createStaff,
  getStaffStatusHistory,
  listDepartments,
  listStaff,
  listUsers,
  updateStaff,
  type Department,
  type Paginated,
  type StaffProfile,
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

vi.mock('@/lib/organization', async (importOriginal) => {
  const original =
    await importOriginal<typeof import('@/lib/organization')>()
  return {
    ...original,
    createStaff: vi.fn(),
    getStaffStatusHistory: vi.fn(),
    listDepartments: vi.fn(),
    listStaff: vi.fn(),
    listUsers: vi.fn(),
    updateStaff: vi.fn(),
  }
})

const departmentsPage: Paginated<Department> = {
  count: 1,
  next: null,
  previous: null,
  results: [
    {
      id: 1,
      name: 'Outpatient',
      code: 'OPD',
      description: '',
      is_active: true,
      created_by: 'admin',
      created_at: '2026-11-26T00:00:00Z',
      updated_at: '2026-11-26T00:00:00Z',
    },
  ],
}

// What a non-Admin sees in the directory: no phone, email or blood group
// (the backend strips them — Spec 003 Permissions table).
const staffPage: Paginated<StaffProfile> = {
  count: 1,
  next: null,
  previous: null,
  results: [
    {
      id: 1,
      staff_id: 'STF-2026-0001',
      full_name: 'Dr Ayesha Khan',
      job_title: 'Medical Officer',
      department: 1,
      role: 'doctor',
      user: 2,
      status: 'active',
      created_by: 'admin',
      created_at: '2026-11-26T00:00:00Z',
      updated_at: '2026-11-26T00:00:00Z',
    },
  ],
}

const staffPageAdmin = {
  ...staffPage,
  results: [
    {
      ...staffPage.results[0],
      phone: '03001234567',
      email: 'ayesha@example.com',
      blood_group: 'O+',
    },
  ],
}

function renderPage() {
  return render(
    <MemoryRouter>
      <StaffPage />
    </MemoryRouter>,
  )
}

describe('StaffPage', () => {
  beforeEach(() => {
    currentUser = adminUser
    vi.mocked(listStaff).mockReset().mockResolvedValue(staffPageAdmin)
    vi.mocked(listDepartments)
      .mockReset()
      .mockResolvedValue(departmentsPage)
    vi.mocked(listUsers).mockReset().mockResolvedValue({
      count: 0,
      next: null,
      previous: null,
      results: [],
    })
    vi.mocked(createStaff).mockReset()
    vi.mocked(updateStaff).mockReset()
    vi.mocked(getStaffStatusHistory).mockReset()
  })

  it('renders the staff directory with department names resolved', async () => {
    renderPage()
    expect(await screen.findByText('Dr Ayesha Khan')).toBeInTheDocument()
    expect(screen.getByText('STF-2026-0001')).toBeInTheDocument()
    expect(screen.getByText('Medical Officer')).toBeInTheDocument()
    expect(screen.getByText('Outpatient')).toBeInTheDocument()
    expect(screen.getByText('03001234567')).toBeInTheDocument()
  })

  it('hides mutation controls and contact details from non-Admin roles', async () => {
    currentUser = doctorUser
    vi.mocked(listStaff).mockResolvedValue(staffPage)
    renderPage()
    expect(await screen.findByText('Dr Ayesha Khan')).toBeInTheDocument()
    expect(screen.queryByText('New staff member')).not.toBeInTheDocument()
    expect(screen.queryByText('Edit')).not.toBeInTheDocument()
    expect(screen.queryByText('03001234567')).not.toBeInTheDocument()
    expect(screen.queryByText('ayesha@example.com')).not.toBeInTheDocument()
  })

  it('requires a reason when changing a staff status', async () => {
    const user = userEvent.setup()
    renderPage()
    await user.click(await screen.findByText('Edit'))
    await user.selectOptions(screen.getByLabelText('Status'), 'inactive')
    expect(screen.getByLabelText('Reason for status change')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Save changes' }))
    await waitFor(() =>
      expect(
        screen.getByText('A reason is required when changing staff status.'),
      ).toBeInTheDocument(),
    )
    expect(updateStaff).not.toHaveBeenCalled()
  })

  it('sends the status reason when the status changes', async () => {
    const user = userEvent.setup()
    vi.mocked(updateStaff).mockResolvedValue({
      ...staffPageAdmin.results[0],
      status: 'inactive',
    })
    renderPage()
    await user.click(await screen.findByText('Edit'))
    await user.selectOptions(screen.getByLabelText('Status'), 'inactive')
    await user.type(
      screen.getByLabelText('Reason for status change'),
      'Resigned',
    )
    await user.click(screen.getByRole('button', { name: 'Save changes' }))
    await waitFor(() =>
      expect(updateStaff).toHaveBeenCalledWith(
        1,
        expect.objectContaining({
          status: 'inactive',
          status_reason: 'Resigned',
        }),
      ),
    )
  })

  it('shows the status history for a staff member', async () => {
    const user = userEvent.setup()
    vi.mocked(getStaffStatusHistory).mockResolvedValue({
      count: 1,
      next: null,
      previous: null,
      results: [
        {
          id: 1,
          previous_status: 'active',
          new_status: 'inactive',
          reason: 'Resigned',
          actor: 'admin',
          timestamp: '2026-11-27T00:00:00Z',
        },
      ],
    })
    renderPage()
    await user.click(await screen.findByText('History'))
    expect(await screen.findByText(/Resigned/)).toBeInTheDocument()
    expect(screen.getByText(/Active → Inactive/)).toBeInTheDocument()
    expect(getStaffStatusHistory).toHaveBeenCalledWith(1)
  })

  it('shows the backend field error when a clinical role has no department', async () => {
    const user = userEvent.setup()
    vi.mocked(createStaff).mockRejectedValue(
      new ApiError(400, 'department: Department is required for clinical roles.', {
        department: ['Department is required for clinical roles.'],
      }),
    )
    renderPage()
    await user.click(await screen.findByText('New staff member'))
    await user.type(screen.getByLabelText('Full name'), 'Dr New Person')
    await user.type(screen.getByLabelText('Job title'), 'Medical Officer')
    await user.selectOptions(screen.getByLabelText('System role'), 'doctor')
    await user.click(screen.getByRole('button', { name: 'Create staff member' }))
    await waitFor(() =>
      expect(
        screen.getByText('Department is required for clinical roles.'),
      ).toBeInTheDocument(),
    )
  })
})
