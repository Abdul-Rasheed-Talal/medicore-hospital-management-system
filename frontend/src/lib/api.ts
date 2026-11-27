/**
 * API client for the Django backend (session auth, spec D-09 / ADR-001).
 *
 * - Same-origin in dev (Vite proxies /api to localhost:8000) and in
 *   production behind a single host; override with VITE_API_URL if the
 *   API lives elsewhere.
 * - `credentials: "include"` sends the HttpOnly session cookie.
 * - Unsafe methods send the CSRF token from the `csrftoken` cookie as
 *   `X-CSRFToken`; call `ensureCsrf()` (or hit GET /api/auth/csrf/)
 *   before the first login attempt so the cookie exists.
 */

const API_BASE = import.meta.env.VITE_API_URL ?? ''

function getCookie(name: string): string | null {
  const match = document.cookie
    .split('; ')
    .find((row) => row.startsWith(`${name}=`))
  return match ? decodeURIComponent(match.split('=')[1]) : null
}

export async function ensureCsrf(): Promise<void> {
  await fetch(`${API_BASE}/api/auth/csrf/`, { credentials: 'include' })
}

export class ApiError extends Error {
  status: number
  detail: string
  /** DRF field errors, when the backend returned them (e.g. duplicate
   * code, missing required field). Keyed by field name. */
  fieldErrors?: Record<string, string[]>

  constructor(
    status: number,
    detail: string,
    fieldErrors?: Record<string, string[]>,
  ) {
    super(detail)
    this.status = status
    this.detail = detail
    this.fieldErrors = fieldErrors
  }
}

export interface ApiOptions extends RequestInit {
  /** Skip the CSRF header (safe methods only). Defaults to method-based. */
  skipCsrf?: boolean
}

export async function api<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const { skipCsrf, headers, ...init } = options
  const method = (init.method ?? 'GET').toUpperCase()
  const unsafe = !['GET', 'HEAD', 'OPTIONS'].includes(method)

  const requestHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(headers as Record<string, string> | undefined),
  }
  if (unsafe && !skipCsrf) {
    const token = getCookie('csrftoken')
    if (token) requestHeaders['X-CSRFToken'] = token
  }

  const response = await fetch(`${API_BASE}${path}`, {
    credentials: 'include',
    headers: requestHeaders,
    ...init,
  })

  if (response.status === 204) return undefined as T

  let payload: unknown = null
  try {
    payload = await response.json()
  } catch {
    payload = null
  }

  if (!response.ok) {
    // DRF validation errors arrive as {"field": ["message", ...]} (or a
    // {"detail": "..."} string). Keep them structured so forms can show
    // field-level errors, and join them into `detail` for plain display.
    const payloadObj =
      payload && typeof payload === 'object' && !Array.isArray(payload)
        ? (payload as Record<string, unknown>)
        : null
    const fieldErrors: Record<string, string[]> = {}
    if (payloadObj) {
      for (const [key, value] of Object.entries(payloadObj)) {
        if (key === 'detail') continue
        if (Array.isArray(value)) fieldErrors[key] = value.map(String)
        else if (typeof value === 'string') fieldErrors[key] = [value]
      }
    }
    const hasFieldErrors = Object.keys(fieldErrors).length > 0
    const detail =
      (payloadObj?.detail as string | undefined) ??
      // Django password validation returns {"new_password": [...]}; keep
      // surfacing those messages directly, as before.
      (Array.isArray(payloadObj?.new_password)
        ? (payloadObj.new_password as unknown[]).map(String).join(' ')
        : undefined) ??
      (hasFieldErrors
        ? Object.entries(fieldErrors)
            .map(([key, messages]) => `${key}: ${messages.join(' ')}`)
            .join(' ')
        : `Request failed (${response.status})`)
    throw new ApiError(
      response.status,
      detail,
      hasFieldErrors ? fieldErrors : undefined,
    )
  }
  return payload as T
}
