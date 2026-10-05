/** The one place that talks to the backend. Everything else goes through TanStack Query.
 *
 *  The browser only calls its own origin under /api: Vite (dev) and nginx (production)
 *  forward /api/* to the backend with the prefix removed, so no CORS is involved. */
const BASE = '/api'

/** A failed request, kept in a shape the UI can turn into a sentence (see lib/copy.ts). */
export class ApiError extends Error {
  /** HTTP status, or 0 when the server could not be reached at all. */
  readonly status: number
  /** The backend's own explanation (`{"detail": "..."}`), when it gave one. */
  readonly detail: string | null

  constructor(status: number, detail: string | null) {
    super(detail ?? `Request failed (${status})`)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

async function readDetail(response: Response): Promise<string | null> {
  try {
    const body: unknown = await response.json()
    if (typeof body === 'object' && body !== null && 'detail' in body) {
      const { detail } = body
      if (typeof detail === 'string') return detail
    }
  } catch {
    // Not JSON: fall through to "no detail".
  }
  return null
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${BASE}${path}`, init)
  } catch {
    throw new ApiError(0, null)
  }
  if (!response.ok) {
    throw new ApiError(response.status, await readDetail(response))
  }
  if (response.status === 204) return undefined as T // nothing to read back (a delete)
  return (await response.json()) as T
}

export function postJson<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export function putJson<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

/** Query string from only the values that are set. */
export function query(params: Record<string, string | number | undefined | null>): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') search.set(key, String(value))
  }
  const text = search.toString()
  return text ? `?${text}` : ''
}
