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

  constructor(status: number, detail: string) {
    super(detail)
    this.status = status
    this.detail = detail
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
    const detail =
      (payload as { detail?: string } | null)?.detail ??
      `Request failed (${response.status})`
    throw new ApiError(response.status, detail)
  }
  return payload as T
}
