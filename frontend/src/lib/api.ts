// Klien HTTP tunggal untuk semua panggilan ke backend lewat gateway (/api/*).

export const ACCESS_TOKEN_KEY = 'sg_access_token'
export const REFRESH_TOKEN_KEY = 'sg_refresh_token'

const REFRESH_PATH = '/api/identity/auth/refresh'
// Layanan yang masih memakai sistem akun lama (belum dipindah ke identity).
const LEGACY_PREFIXES = ['/api/micro-cred/']
const LEGACY_MESSAGE = 'Fitur ini belum tersedia untuk akun Anda karena sedang dipindahkan ke sistem akun yang baru.'

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
  getRefresh(): string | null {
    if (typeof window === 'undefined') return null
    return window.localStorage.getItem(REFRESH_TOKEN_KEY)
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
  /** Kirim header Authorization (default true). Matikan untuk login. */
  auth?: boolean
  /** Kembalikan isi respons sukses sebagai Blob (untuk mengunduh berkas yang butuh token). */
  blob?: boolean
}

type RefreshResult = 'ok' | 'ditolak' | 'jaringan'

/**
 * Perbarui access token memakai refresh token (sekali pakai).
 * Refresh token berotasi, jadi dua permintaan bersamaan tidak boleh memakainya dua kali: bila terjadi,
 * server menganggapnya dicuri dan mencabut seluruh sesi. Karena itu satu proses per tab (`inflight`)
 * dan satu proses lintas tab (Web Locks), dengan pemeriksaan ulang setelah mendapat kunci.
 */
let inflight: Promise<RefreshResult> | null = null

async function refreshSekali(tokenGagal: string): Promise<RefreshResult> {
  const jalankan = async (): Promise<RefreshResult> => {
    const sekarang = tokenStore.get()
    if (sekarang && sekarang !== tokenGagal) return 'ok' // tab atau permintaan lain sudah memperbarui
    const refresh = tokenStore.getRefresh()
    if (!refresh) return 'ditolak'
    let response: Response
    try {
      response = await fetch(REFRESH_PATH, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refresh }),
      })
    } catch {
      return 'jaringan'
    }
    if (!response.ok) return response.status >= 500 ? 'jaringan' : 'ditolak'
    const data = (await response.json()) as { access_token: string; refresh_token?: string | null }
    tokenStore.set(data.access_token, data.refresh_token)
    return 'ok'
  }

  if (!inflight) {
    const locks = typeof navigator !== 'undefined' ? (navigator as Navigator & { locks?: LockManager }).locks : undefined
    inflight = (locks ? locks.request('sg-token-refresh', jalankan) : jalankan()).finally(() => {
      inflight = null
    })
  }
  return inflight
}

async function kirim(path: string, options: ApiOptions, token: string | null): Promise<{ response: Response; data: unknown }> {
  const { json, auth = true, headers, body, blob = false, ...init } = options
  const requestHeaders = new Headers(headers)
  if (auth && token) requestHeaders.set('Authorization', `Bearer ${token}`)

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

  if (blob && response.ok) return { response, data: await response.blob() }

  const text = await response.text()
  let data: unknown = null
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      data = text
    }
  }
  return { response, data }
}

function keluarkanSesi() {
  tokenStore.clear()
  if (typeof window !== 'undefined' && window.location.pathname !== '/login') window.location.assign('/login')
}

export async function apiFetch<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const auth = options.auth ?? true
  let tokenDipakai = auth ? tokenStore.get() : null
  let { response, data } = await kirim(path, options, tokenDipakai)
  let sesiBerakhir = false

  // Access token identity hanya berlaku 15 menit: coba perbarui diam-diam sekali, lalu ulangi.
  if (response.status === 401 && auth && tokenDipakai && path !== REFRESH_PATH) {
    const hasil = await refreshSekali(tokenDipakai)
    if (hasil === 'jaringan') throw new ApiError('Tidak dapat memperbarui sesi. Periksa koneksi Anda.', 0)
    if (hasil === 'ok') {
      tokenDipakai = tokenStore.get()
      ;({ response, data } = await kirim(path, options, tokenDipakai))
    } else {
      sesiBerakhir = true
    }
  }

  if (!response.ok) {
    if (response.status === 401 && auth) {
      // Layanan lama menolak token identity: sesi masih sah, jangan keluarkan pengguna.
      if (!sesiBerakhir && LEGACY_PREFIXES.some((prefix) => path.startsWith(prefix))) {
        throw new ApiError(LEGACY_MESSAGE, 401)
      }
      keluarkanSesi()
    }
    throw new ApiError(messageFromBody(data, response.status), response.status)
  }

  return data as T
}

export function errorMessage(error: unknown, fallback = 'Terjadi kesalahan. Coba lagi.'): string {
  return error instanceof Error && error.message ? error.message : fallback
}
