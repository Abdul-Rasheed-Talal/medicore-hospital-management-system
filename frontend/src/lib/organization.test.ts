import { describe, expect, it, vi, beforeEach } from 'vitest'
import {
  createDepartment,
  createService,
  createStaff,
  deleteDepartment,
  getStaffStatusHistory,
  listDepartments,
  listServices,
  listStaff,
  listUsers,
  updateDepartment,
  updateStaff,
} from '@/lib/organization'

function jsonResponse(status: number, payload: unknown): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => payload,
  } as Response
}

describe('organization API client', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  it('lists departments from the paginated endpoint', async () => {
    const page = {
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
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse(200, page))
    const data = await listDepartments()
    expect(fetch).toHaveBeenCalledWith(
      '/api/departments/',
      expect.objectContaining({ credentials: 'include' }),
    )
    expect(data.results).toHaveLength(1)
    expect(data.results[0].code).toBe('OPD')
  })

  it('filters the department list by active flag', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse(200, { count: 0, next: null, previous: null, results: [] }),
    )
    await listDepartments({ is_active: true })
    expect(fetch).toHaveBeenCalledWith(
      '/api/departments/?is_active=true',
      expect.objectContaining({ credentials: 'include' }),
    )
  })

  it('creates a department with a POST', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse(201, { id: 2, name: 'Laboratory', code: 'LAB' }),
    )
    const created = await createDepartment({
      name: 'Laboratory',
      code: 'LAB',
      description: '',
    })
    expect(fetch).toHaveBeenCalledWith(
      '/api/departments/',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ name: 'Laboratory', code: 'LAB', description: '' }),
      }),
    )
    expect(created.id).toBe(2)
  })

  it('returns the deactivation warning from a department update', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse(200, {
        id: 1,
        name: 'Outpatient',
        code: 'OPD',
        is_active: false,
        warning: 'This department still has 2 active staff member(s).',
      }),
    )
    const updated = await updateDepartment(1, { is_active: false })
    expect(fetch).toHaveBeenCalledWith(
      '/api/departments/1/',
      expect.objectContaining({ method: 'PATCH' }),
    )
    expect(updated.warning).toContain('2 active staff')
  })

  it('deletes a department with a DELETE', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      status: 204,
      json: async () => null,
    } as Response)
    await deleteDepartment(1)
    expect(fetch).toHaveBeenCalledWith(
      '/api/departments/1/',
      expect.objectContaining({ method: 'DELETE' }),
    )
  })

  it('lists staff with a status filter', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse(200, { count: 0, next: null, previous: null, results: [] }),
    )
    await listStaff({ status: 'active' })
    expect(fetch).toHaveBeenCalledWith(
      '/api/staff/?status=active',
      expect.objectContaining({ credentials: 'include' }),
    )
  })

  it('creates a staff profile with a POST', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse(201, { id: 1, staff_id: 'STF-2026-0001' }),
    )
    const created = await createStaff({
      full_name: 'Dr Ayesha Khan',
      job_title: 'Medical Officer',
      department: 1,
      role: 'doctor',
      user: null,
      phone: '',
      email: '',
      blood_group: null,
    })
    expect(fetch).toHaveBeenCalledWith(
      '/api/staff/',
      expect.objectContaining({ method: 'POST' }),
    )
    expect(created.staff_id).toBe('STF-2026-0001')
  })

  it('sends the status reason when a staff status changes', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse(200, { id: 1, status: 'inactive' }),
    )
    await updateStaff(1, { status: 'inactive', status_reason: 'Resigned' })
    expect(fetch).toHaveBeenCalledWith(
      '/api/staff/1/',
      expect.objectContaining({
        method: 'PATCH',
        body: JSON.stringify({ status: 'inactive', status_reason: 'Resigned' }),
      }),
    )
  })

  it('loads a staff member’s status history', async () => {
    const history = [
      {
        id: 1,
        previous_status: 'active',
        new_status: 'inactive',
        reason: 'Resigned',
        actor: 'admin',
        timestamp: '2026-11-27T00:00:00Z',
      },
    ]
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse(200, { count: 1, next: null, previous: null, results: history }),
    )
    const data = await getStaffStatusHistory(1)
    expect(fetch).toHaveBeenCalledWith(
      '/api/staff/1/status-history/',
      expect.objectContaining({ credentials: 'include' }),
    )
    expect(data.results[0].reason).toBe('Resigned')
  })

  it('lists services and users for the service form', async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(
        jsonResponse(200, { count: 0, next: null, previous: null, results: [] }),
      )
      .mockResolvedValueOnce(
        jsonResponse(200, { count: 0, next: null, previous: null, results: [] }),
      )
    await listServices()
    await listUsers()
    expect(fetch).toHaveBeenNthCalledWith(
      1,
      '/api/services/',
      expect.objectContaining({ credentials: 'include' }),
    )
    expect(fetch).toHaveBeenNthCalledWith(
      2,
      '/api/users/',
      expect.objectContaining({ credentials: 'include' }),
    )
  })

  it('creates a service with a POST', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse(201, { id: 1, name: 'General Consultation', code: 'CONS-GEN' }),
    )
    const created = await createService({
      name: 'General Consultation',
      code: 'CONS-GEN',
      category: 1,
      department: 1,
    })
    expect(fetch).toHaveBeenCalledWith(
      '/api/services/',
      expect.objectContaining({ method: 'POST' }),
    )
    expect(created.code).toBe('CONS-GEN')
  })
})
