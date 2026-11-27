import { apiFetch, tokenStore } from '@/src/lib/api'

/** Pengguna untuk tampilan. Sumber: layanan identity (GET /api/identity/auth/saya). */
export interface AuthUser {
  id: string
  email: string
  full_name: string | null
  nim: string | null
  faculty: string | null
  study_program: string | null
  /** Peran aktif, misalnya ["mahasiswa"] atau ["dosen_pa", "kaprodi"]. */
  roles: string[]
  mustChangePassword: boolean
  /** Unit tempat setiap peran berlaku, misalnya kaprodi pada prodi tertentu. */
  units: UnitPeran[]
  panduanPribadi: boolean
  prodiTerbuka: boolean
  prodiIsian: string | null
  ptIsian: string | null
}

export interface UnitPeran {
  peran: string
  tipe: string
  id?: string
  nama?: string | null
}

export interface RegisterInput {
  nama_lengkap: string
  email: string
  sandi: string
  program_studi: string
  perguruan_tinggi: string
}

interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  wajib_ganti_sandi: boolean
  peran: string[]
}

interface ProfilResponse {
  id: string
  nama_lengkap: string
  nim: string | null
  email: string
  wajib_ganti_sandi: boolean
  peran: string[]
  unit?: UnitPeran[]
  prodi_isian?: string | null
  pt_isian?: string | null
  panduan_pribadi?: boolean
  akademik: {
    prodi: { nama: string; terbuka?: boolean }
    fakultas: { nama: string } | null
  } | null
}

const BASE = '/api/identity'

function mapUser(profil: ProfilResponse): AuthUser {
  return {
    id: profil.id,
    email: profil.email,
    full_name: profil.nama_lengkap,
    nim: profil.nim,
    faculty: profil.akademik?.fakultas?.nama ?? null,
    study_program: profil.akademik?.prodi.nama ?? null,
    roles: profil.peran,
    mustChangePassword: profil.wajib_ganti_sandi,
    units: profil.unit ?? [],
    panduanPribadi: Boolean(profil.panduan_pribadi),
    prodiTerbuka: Boolean(profil.akademik?.prodi.terbuka ?? profil.panduan_pribadi),
    prodiIsian: profil.prodi_isian ?? null,
    ptIsian: profil.pt_isian ?? null,
  }
}

export const authService = {
  async statusRegistrasi(): Promise<boolean> {
    const r = await apiFetch<{ aktif: boolean }>(`${BASE}/auth/registrasi`, { auth: false })
    return Boolean(r.aktif)
  },

  async register(input: RegisterInput): Promise<AuthUser> {
    const tokens = await apiFetch<TokenResponse>(`${BASE}/auth/register`, {
      method: 'POST',
      json: input,
      auth: false,
    })
    tokenStore.set(tokens.access_token, tokens.refresh_token)
    return this.me()
  },

  /** Masuk dengan email dan sandi. */
  async login(email: string, password: string): Promise<AuthUser> {
    const tokens = await apiFetch<TokenResponse>(`${BASE}/auth/login`, {
      method: 'POST',
      json: { email, sandi: password },
      auth: false,
    })
    tokenStore.set(tokens.access_token, tokens.refresh_token)
    return this.me()
  },

  async me(): Promise<AuthUser> {
    return mapUser(await apiFetch<ProfilResponse>(`${BASE}/auth/saya`))
  },

  /** Ganti kata sandi. Server membatalkan token lama dan mengembalikan token baru, yang langsung disimpan. */
  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    const tokens = await apiFetch<TokenResponse>(`${BASE}/auth/ganti-sandi`, {
      method: 'POST',
      json: { sandi_lama: currentPassword, sandi_baru: newPassword },
    })
    tokenStore.set(tokens.access_token, tokens.refresh_token)
  },

  /** Keluar: cabut refresh token di server (tanpa menunggu hasilnya), lalu hapus sesi lokal. */
  logout() {
    const refresh = tokenStore.getRefresh()
    if (refresh && tokenStore.get()) {
      void apiFetch(`${BASE}/auth/logout`, { method: 'POST', json: { refresh_token: refresh } }).catch(() => undefined)
    }
    tokenStore.clear()
  },
}
