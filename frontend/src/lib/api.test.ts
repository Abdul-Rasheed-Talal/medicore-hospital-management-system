import { describe, expect, it, vi, beforeEach } from 'vitest'
import { api, ApiError } from '@/lib/api'

function jsonResponse(status: number, payload: unknown): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => payload,
  } as Response
}

describe('api client', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  it('returns parsed JSON on success', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse(200, { id: 1, name: 'Outpatient' }),
    )
    const data = await api<{ id: number; name: string }>('/api/departments/1/')
    expect(data).toEqual({ id: 1, name: 'Outpatient' })
    expect(fetch).toHaveBeenCalledWith(
      '/api/departments/1/',
      expect.objectContaining({ credentials: 'include' }),
    )
  })

  it('surfaces a detail message from the backend', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse(403, { detail: 'You do not have permission.' }),
    )
    await expect(api('/api/departments/')).rejects.toMatchObject({
      status: 403,
      detail: 'You do not have permission.',
    })
  })

  it('parses DRF field errors onto ApiError.fieldErrors', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse(400, {
        code: ['A department with this code already exists.'],
      }),
    )
    let caught: unknown
    try {
      await api('/api/departments/', { method: 'POST', body: '{}' })
    } catch (error) {
      caught = error
    }
    expect(caught).toBeInstanceOf(ApiError)
    const apiError = caught as ApiError
    expect(apiError.status).toBe(400)
    expect(apiError.fieldErrors).toEqual({
      code: ['A department with this code already exists.'],
    })
    expect(apiError.detail).toContain('code')
    expect(apiError.detail).toContain('already exists')
  })

  it('keeps the existing new_password error behaviour', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse(400, { new_password: ['This password is too short.'] }),
    )
    let caught: unknown
    try {
      await api('/api/auth/change-password/', { method: 'POST', body: '{}' })
    } catch (error) {
      caught = error
    }
    expect(caught).toBeInstanceOf(ApiError)
    expect((caught as ApiError).detail).toBe('This password is too short.')
    expect((caught as ApiError).fieldErrors).toEqual({
      new_password: ['This password is too short.'],
    })
  })
})
