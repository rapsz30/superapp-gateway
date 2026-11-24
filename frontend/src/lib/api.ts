// Klien HTTP tunggal untuk semua panggilan ke backend lewat gateway (/api/*).

export const ACCESS_TOKEN_KEY = 'sg_access_token'
export const REFRESH_TOKEN_KEY = 'sg_refresh_token'

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export const tokenStore = {
  get(): string | null {
    if (typeof window === 'undefined') return null
    return window.localStorage.getItem(ACCESS_TOKEN_KEY)
  },
  set(accessToken: string, refreshToken?: string | null) {
    window.localStorage.setItem(ACCESS_TOKEN_KEY, accessToken)
    if (refreshToken) window.localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken)
  },
  clear() {
    if (typeof window === 'undefined') return
    window.localStorage.removeItem(ACCESS_TOKEN_KEY)
    window.localStorage.removeItem(REFRESH_TOKEN_KEY)
  },
}

function messageFromBody(body: unknown, status: number): string {
  if (body && typeof body === 'object') {
    const record = body as Record<string, unknown>
    const detail = record.detail ?? record.error ?? record.message
    if (typeof detail === 'string' && detail.trim()) return detail
    if (Array.isArray(detail) && detail.length) {
      const first = detail[0] as { msg?: unknown; loc?: unknown }
      if (first && typeof first.msg === 'string') {
        const field = Array.isArray(first.loc) ? String(first.loc[first.loc.length - 1]) : ''
        return field ? `${field}: ${first.msg}` : first.msg
      }
    }
  }
  if (typeof body === 'string' && body.trim() && body.length < 300) return body
  if (status === 502 || status === 503 || status === 504) return 'Layanan sedang tidak tersedia. Coba lagi beberapa saat lagi.'
  return `Permintaan gagal (HTTP ${status}).`
}

type ApiOptions = Omit<RequestInit, 'body'> & {
  json?: unknown
  body?: BodyInit | null
  /** Kirim header Authorization (default true). Matikan untuk login dan register. */
  auth?: boolean
}

export async function apiFetch<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const { json, auth = true, headers, body, ...init } = options
  const requestHeaders = new Headers(headers)
  if (auth) {
    const token = tokenStore.get()
    if (token) requestHeaders.set('Authorization', `Bearer ${token}`)
  }

  let requestBody: BodyInit | null | undefined = body
  if (json !== undefined) {
    requestHeaders.set('Content-Type', 'application/json')
    requestBody = JSON.stringify(json)
  }

  let response: Response
  try {
    response = await fetch(path, { ...init, headers: requestHeaders, body: requestBody })
  } catch {
    throw new ApiError('Tidak dapat terhubung ke server. Periksa koneksi Anda.', 0)
  }

  const text = await response.text()
  let data: unknown = null
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      data = text
    }
  }

  if (!response.ok) {
    if (response.status === 401 && auth) {
      tokenStore.clear()
      if (typeof window !== 'undefined' && window.location.pathname !== '/login') window.location.assign('/login')
    }
    throw new ApiError(messageFromBody(data, response.status), response.status)
  }

  return data as T
}

export function errorMessage(error: unknown, fallback = 'Terjadi kesalahan. Coba lagi.'): string {
  return error instanceof Error && error.message ? error.message : fallback
}
