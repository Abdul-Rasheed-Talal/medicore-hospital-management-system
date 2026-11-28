import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import ServicesPage from '@/pages/setup/ServicesPage'
import { ApiError } from '@/lib/api'
import type { SessionUser } from '@/context/AuthContext'
import {
  createService,
  createServiceCategory,
  createVisitType,
  listDepartments,
  listServiceCategories,
  listServices,
  listVisitTypes,
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
    createService: vi.fn(),
    createServiceCategory: vi.fn(),
    createVisitType: vi.fn(),
    deleteService: vi.fn(),
    deleteServiceCategory: vi.fn(),
    deleteVisitType: vi.fn(),
    listDepartments: vi.fn(),
    listServiceCategories: vi.fn(),
    listServices: vi.fn(),
    listVisitTypes: vi.fn(),
    updateService: vi.fn(),
    updateServiceCategory: vi.fn(),
    updateVisitType: vi.fn(),
  }
})

const servicesPage = {
  count: 1,
  next: null,
  previous: null,
  results: [
    {
      id: 1,
      name: 'General Consultation',
      code: 'CONS-GEN',
      category: 1,
      department: 1,
      is_active: true,
      created_by: 'admin',
      created_at: '2026-11-26T00:00:00Z',
      updated_at: '2026-11-26T00:00:00Z',
    },
  ],
}

const categoriesPage = {
  count: 1,
  next: null,
  previous: null,
  results: [
    {
      id: 1,
      name: 'Consultation',
      is_active: true,
      created_by: 'admin',
      created_at: '2026-11-26T00:00:00Z',
      updated_at: '2026-11-26T00:00:00Z',
    },
  ],
}

const visitTypesPage = {
  count: 1,
  next: null,
  previous: null,
  results: [
    {
      id: 1,
      name: 'First visit',
      is_active: true,
      created_by: 'admin',
      created_at: '2026-11-26T00:00:00Z',
      updated_at: '2026-11-26T00:00:00Z',
    },
  ],
}

const departmentsPage = {
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

function renderPage() {
  return render(
    <MemoryRouter>
      <ServicesPage />
    </MemoryRouter>,
  )
}

describe('ServicesPage', () => {
  beforeEach(() => {
    currentUser = adminUser
    vi.mocked(listServices).mockReset().mockResolvedValue(servicesPage)
    vi.mocked(listServiceCategories)
      .mockReset()
      .mockResolvedValue(categoriesPage)
    vi.mocked(listVisitTypes).mockReset().mockResolvedValue(visitTypesPage)
    vi.mocked(listDepartments).mockReset().mockResolvedValue(departmentsPage)
    vi.mocked(createService).mockReset()
    vi.mocked(createServiceCategory).mockReset()
    vi.mocked(createVisitType).mockReset()
  })

  it('renders the service list with category and department names resolved', async () => {
    renderPage()
    expect(await screen.findByText('General Consultation')).toBeInTheDocument()
    expect(screen.getByText('CONS-GEN')).toBeInTheDocument()
    expect(screen.getByText('Consultation')).toBeInTheDocument()
    expect(screen.getByText('Outpatient')).toBeInTheDocument()
  })

  it('lists service categories on the Categories tab and creates one', async () => {
    const user = userEvent.setup()
    vi.mocked(createServiceCategory).mockResolvedValue({
      id: 2,
      name: 'Imaging',
      is_active: true,
      created_by: 'admin',
      created_at: '2026-11-27T00:00:00Z',
      updated_at: '2026-11-27T00:00:00Z',
    })
    renderPage()
    await user.click(await screen.findByRole('button', { name: 'Categories' }))
    expect(await screen.findByText('Consultation')).toBeInTheDocument()
    await user.click(screen.getByText('New category'))
    await user.type(screen.getByLabelText('Name'), 'Imaging')
    await user.click(screen.getByRole('button', { name: 'Create category' }))
    await waitFor(() =>
      expect(createServiceCategory).toHaveBeenCalledWith({ name: 'Imaging' }),
    )
  })

  it('lists visit types on the Visit types tab', async () => {
    const user = userEvent.setup()
    renderPage()
    await user.click(await screen.findByRole('button', { name: 'Visit types' }))
    expect(await screen.findByText('First visit')).toBeInTheDocument()
    expect(listVisitTypes).toHaveBeenCalled()
  })

  it('hides all mutation controls from non-Admin roles', async () => {
    currentUser = doctorUser
    renderPage()
    expect(await screen.findByText('General Consultation')).toBeInTheDocument()
    expect(screen.queryByText('New service')).not.toBeInTheDocument()
    expect(screen.queryByText('Edit')).not.toBeInTheDocument()
  })

  it('shows the backend field error when the service code already exists', async () => {
    const user = userEvent.setup()
    vi.mocked(createService).mockRejectedValue(
      new ApiError(400, 'code: A service with this code already exists.', {
        code: ['A service with this code already exists.'],
      }),
    )
    renderPage()
    await user.click(await screen.findByText('New service'))
    await user.type(screen.getByLabelText('Name'), 'General Consultation')
    await user.type(screen.getByLabelText('Code'), 'CONS-GEN')
    await user.selectOptions(screen.getByLabelText('Category'), '1')
    await user.click(screen.getByRole('button', { name: 'Create service' }))
    await waitFor(() =>
      expect(
        screen.getByText('A service with this code already exists.'),
      ).toBeInTheDocument(),
    )
  })

  it('hides a deactivated category from the new-service form (FR-005)', async () => {
    const user = userEvent.setup()
    vi.mocked(listServiceCategories).mockResolvedValue({
      count: 2,
      next: null,
      previous: null,
      results: [
        {
          id: 1,
          name: 'Consultation',
          is_active: true,
          created_by: 'admin',
          created_at: '2026-11-26T00:00:00Z',
          updated_at: '2026-11-26T00:00:00Z',
        },
        {
          id: 2,
          name: 'Imaging',
          is_active: false,
          created_by: 'admin',
          created_at: '2026-11-26T00:00:00Z',
          updated_at: '2026-11-26T00:00:00Z',
        },
      ],
    })
    renderPage()
    await user.click(await screen.findByText('New service'))
    const categorySelect = screen.getByLabelText('Category')
    expect(
      within(categorySelect).getByRole('option', { name: 'Consultation' }),
    ).toBeInTheDocument()
    expect(
      within(categorySelect).queryByRole('option', { name: 'Imaging' }),
    ).not.toBeInTheDocument()
    // The deactivated category is still managed on the Categories tab.
    await user.click(screen.getByRole('button', { name: 'Cancel' }))
    await user.click(screen.getByRole('button', { name: 'Categories' }))
    expect(await screen.findByText('Imaging')).toBeInTheDocument()
  })

  it('keeps a deactivated category when editing the service that uses it', async () => {
    const user = userEvent.setup()
    vi.mocked(listServiceCategories).mockResolvedValue({
      count: 2,
      next: null,
      previous: null,
      results: [
        {
          id: 1,
          name: 'Consultation',
          is_active: true,
          created_by: 'admin',
          created_at: '2026-11-26T00:00:00Z',
          updated_at: '2026-11-26T00:00:00Z',
        },
        {
          id: 2,
          name: 'Imaging',
          is_active: false,
          created_by: 'admin',
          created_at: '2026-11-26T00:00:00Z',
          updated_at: '2026-11-26T00:00:00Z',
        },
      ],
    })
    vi.mocked(listServices).mockResolvedValue({
      count: 1,
      next: null,
      previous: null,
      results: [
        {
          id: 1,
          name: 'X-ray',
          code: 'XRAY',
          category: 2,
          department: 1,
          is_active: true,
          created_by: 'admin',
          created_at: '2026-11-26T00:00:00Z',
          updated_at: '2026-11-26T00:00:00Z',
        },
      ],
    })
    renderPage()
    expect(await screen.findByText('X-ray')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Edit' }))
    const categorySelect = screen.getByLabelText('Category')
    expect(
      within(categorySelect).getByRole('option', { name: 'Imaging' }),
    ).toBeInTheDocument()
    expect(categorySelect).toHaveValue('2')
  })
})
