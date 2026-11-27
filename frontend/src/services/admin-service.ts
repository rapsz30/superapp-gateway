import { apiFetch } from '@/src/lib/api'

const BASE = '/api/identity'

export interface Page<T> {
  data: T[]
  total: number
}

export type Jenjang = 'D3' | 'S1' | 'S2' | 'S3' | 'Profesi'
export type Peran = 'superadmin' | 'dekan' | 'kajur' | 'kaprodi' | 'dosen_pa'
export type UnitTipe = 'global' | 'fakultas' | 'jurusan' | 'prodi'

export interface Fakultas { id: string; kode: string; nama: string; aktif: boolean }
export interface Jurusan { id: string; fakultas_id: string; kode: string; nama: string; aktif: boolean }
export interface Prodi {
  id: string
  jurusan_id: string
  kode: string
  nama: string
  jenjang: Jenjang
  maks_sks_semester: number | null
  aktif: boolean
  terbuka?: boolean
}

export interface StrukturProdi { id: string; kode: string; nama: string; jenjang: Jenjang; aktif: boolean }
export interface StrukturJurusan { id: string; kode: string; nama: string; aktif: boolean; prodi: StrukturProdi[] }
export interface StrukturFakultas { id: string; kode: string; nama: string; aktif: boolean; jurusan: StrukturJurusan[] }

export interface AkunRingkas { id: string; email: string; status: string; wajib_ganti_sandi: boolean }
export interface Orang {
  id: string
  nama_lengkap: string
  nim: string | null
  nidn: string | null
  email_kontak: string | null
  prodi_isian?: string | null
  pt_isian?: string | null
  peran: string[]
  akun: AkunRingkas | null
}
export interface Akun {
  id: string
  orang_id: string
  email: string
  status: string
  wajib_ganti_sandi: boolean
  /** Hanya ada sekali, saat akun dibuat atau sandi diatur ulang. */
  sandi_sementara: string | null
}

export interface Penugasan {
  id: string
  orang_id: string
  peran: Peran
  unit_tipe: UnitTipe
  unit_id: string | null
  mulai: string
  selesai: string | null
}
export interface DosenProdiResult {
  orang: Orang
  akun: Akun
  penugasan: Penugasan
}
export interface Keanggotaan {
  id: string
  orang_id: string
  prodi_id: string
  angkatan: number | null
  status: string
  mulai: string
  selesai: string | null
}
export interface Bimbingan { id: string; dosen_id: string; mahasiswa_id: string; mulai: string; selesai: string | null }

export interface Panduan {
  id: string
  prodi_id: string
  versi: number
  judul: string
  berlaku_mulai: string | null
  status: 'draf' | 'aktif' | 'diarsipkan'
  berkas_nama: string
  teks_karakter: number | null
}

export interface AuditEntry {
  id: number
  pelaku_id: string | null
  aksi: string
  objek_tipe: string
  objek_id: string | null
  sebelum: Record<string, unknown> | null
  sesudah: Record<string, unknown> | null
  waktu: string
}

export interface ImporBaris {
  baris?: number
  status: 'ok' | 'gagal'
  alasan?: string
  email?: string
  sandi_sementara?: string
  nama_lengkap?: string
  [kunci: string]: unknown
}
export interface ImporLaporan { total: number; berhasil: number; gagal: number; baris: ImporBaris[] }

export interface ProdiRingkas { id: string; kode: string; nama: string }
export interface ProdiMahasiswa { id: string; kode: string; nama: string; total: number }

export interface AdminRingkasan {
  struktur: { fakultas: number; jurusan: number; prodi: number }
  orang: number
  mahasiswa_aktif: number
  dosen_pa_aktif: number
  kaprodi_aktif: number
  bimbingan_aktif: number
  mahasiswa_tanpa_dpa: number
  akun: {
    dengan_akun: number
    tanpa_akun: number
    wajib_ganti_sandi: number
    status: Record<string, number>
  }
  peran: Record<string, number>
  keanggotaan_status: Record<string, number>
  pengajuan_status: Record<string, number>
  prodi_tanpa_kaprodi: ProdiRingkas[]
  prodi_tanpa_panduan: ProdiRingkas[]
  mahasiswa_per_prodi: ProdiMahasiswa[]
}

type Query = Record<string, string | number | boolean | null | undefined>

/** Susun query string; nilai kosong dibuang. */
export function qs(query: Query = {}): string {
  const p = new URLSearchParams()
  for (const [k, v] of Object.entries(query)) {
    if (v === undefined || v === null || v === '') continue
    p.set(k, String(v))
  }
  const s = p.toString()
  return s ? `?${s}` : ''
}

const post = <T>(path: string, json?: unknown) =>
  apiFetch<T>(`${BASE}${path}`, { method: 'POST', ...(json === undefined ? {} : { json }) })
const patch = <T>(path: string, json: unknown) => apiFetch<T>(`${BASE}${path}`, { method: 'PATCH', json })
const get = <T>(path: string, query?: Query) => apiFetch<T>(`${BASE}${path}${qs(query)}`)

export const adminService = {
  // ---- Struktur ----
  struktur: (semua = true) => get<StrukturFakultas[]>('/struktur', { semua }),
  buatFakultas: (body: { kode: string; nama: string }) => post<Fakultas>('/fakultas', body),
  ubahFakultas: (id: string, body: { nama?: string; aktif?: boolean }) => patch<Fakultas>(`/fakultas/${id}`, body),
  buatJurusan: (body: { fakultas_id: string; kode: string; nama: string }) => post<Jurusan>('/jurusan', body),
  ubahJurusan: (id: string, body: { nama?: string; aktif?: boolean }) => patch<Jurusan>(`/jurusan/${id}`, body),
  ambilProdi: (id: string) => get<Prodi>(`/prodi/${id}`),
  buatProdi: (body: { jurusan_id: string; kode: string; nama: string; jenjang: Jenjang; maks_sks_semester?: number | null }) =>
    post<Prodi>('/prodi', body),
  ubahProdi: (id: string, body: { nama?: string; jenjang?: Jenjang; maks_sks_semester?: number | null; aktif?: boolean }) =>
    patch<Prodi>(`/prodi/${id}`, body),

  // ---- Orang dan akun ----
  daftarOrang: (query: { q?: string; prodi_id?: string; peran?: string; halaman?: number; ukuran?: number }) =>
    get<Page<Orang>>('/orang', query),
  ambilOrang: (id: string) => get<Orang>(`/orang/${id}`),
  buatOrang: (body: { nama_lengkap: string; nim?: string | null; nidn?: string | null; email_kontak?: string | null }) =>
    post<Orang>('/orang', body),
  ubahOrang: (id: string, body: { nama_lengkap?: string; nim?: string | null; nidn?: string | null; email_kontak?: string | null }) =>
    patch<Orang>(`/orang/${id}`, body),
  imporOrang(berkas: File) {
    const form = new FormData()
    form.append('berkas', berkas)
    return apiFetch<ImporLaporan>(`${BASE}/orang/impor`, { method: 'POST', body: form })
  },
  buatAkun: (body: { orang_id: string; email: string; sandi?: string | null }) => post<Akun>('/akun', body),
  buatDosenProdi: (prodiId: string, body: { nama_lengkap: string; nidn?: string | null; email_kontak?: string | null; email: string; sandi: string }) =>
    post<DosenProdiResult>(`/prodi/${prodiId}/dosen`, body),
  aturUlangSandi: (id: string) => post<Akun>(`/akun/${id}/atur-ulang-sandi`),
  ubahStatusAkun: (id: string, status: 'aktif' | 'ditangguhkan' | 'nonaktif') => patch<Akun>(`/akun/${id}/status`, { status }),

  // ---- Penugasan dan keanggotaan ----
  daftarPenugasan: (query: { orang_id?: string; unit_id?: string; peran?: string; aktif?: boolean; halaman?: number; ukuran?: number }) =>
    get<Page<Penugasan>>('/penugasan', query),
  buatPenugasan: (body: { orang_id: string; peran: Peran; unit_tipe: UnitTipe; unit_id: string | null; mulai?: string | null }) =>
    post<Penugasan>('/penugasan', body),
  akhiriPenugasan: (id: string, selesai?: string | null) => post<Penugasan>(`/penugasan/${id}/akhiri`, { selesai: selesai || null }),

  daftarKeanggotaan: (query: { orang_id?: string; prodi_id?: string; aktif?: boolean; halaman?: number; ukuran?: number }) =>
    get<Page<Keanggotaan>>('/keanggotaan', query),
  buatMahasiswaDummy: (prodiId: string, body: { jumlah: number; sandi: string }) =>
    post<{ dibuat: number; akun: { nama: string; email: string }[] }>(`/prodi/${prodiId}/mahasiswa-dummy`, body),
  buatKeanggotaan: (body: { orang_id: string; prodi_id: string; angkatan?: number | null; status?: 'aktif' | 'cuti' }) =>
    post<Keanggotaan>('/keanggotaan', body),
  ubahStatusKeanggotaan: (id: string, status: 'aktif' | 'cuti' | 'lulus' | 'keluar') =>
    post<Keanggotaan>(`/keanggotaan/${id}/status`, { status }),
  pindahProdi: (id: string, body: { prodi_tujuan_id: string; angkatan?: number | null }) =>
    post<Keanggotaan>(`/keanggotaan/${id}/pindah`, body),

  // ---- Bimbingan (dosen PA) ----
  daftarBimbingan: (query: { dosen_id?: string; mahasiswa_id?: string; aktif?: boolean; halaman?: number; ukuran?: number }) =>
    get<Page<Bimbingan>>('/bimbingan', query),
  buatBimbingan: (body: { dosen_id: string; mahasiswa_id: string }) => post<Bimbingan>('/bimbingan', body),
  akhiriBimbingan: (id: string) => post<Bimbingan>(`/bimbingan/${id}/akhiri`, {}),
  pindahkanBimbingan: (body: { dosen_asal_id: string; dosen_tujuan_id: string; mahasiswa_ids?: string[] }) =>
    post<{ dialihkan: number; bimbingan_baru: string[] }>('/bimbingan/pindahkan', body),

  // ---- Panduan akademik ----
  daftarPanduan: (prodiId: string) => get<Page<Panduan>>(`/prodi/${prodiId}/panduan`),
  unggahPanduan(prodiId: string, judul: string, berkas: File, berlakuMulai?: string) {
    const form = new FormData()
    form.append('judul', judul)
    if (berlakuMulai) form.append('berlaku_mulai', berlakuMulai)
    form.append('berkas', berkas)
    return apiFetch<Panduan>(`${BASE}/prodi/${prodiId}/panduan`, { method: 'POST', body: form })
  },
  aktifkanPanduan: (id: string) => post<Panduan>(`/panduan/${id}/aktifkan`),
  /** Berkas PDF butuh token, jadi diambil sebagai Blob lalu dibuka lewat object URL. */
  unduhPanduan: (id: string) => apiFetch<Blob>(`${BASE}/panduan/${id}/berkas`, { blob: true }),

  // ---- Audit ----
  daftarAudit: (query: { aksi?: string; pelaku_id?: string; objek_id?: string; halaman?: number; ukuran?: number }) =>
    get<Page<AuditEntry>>('/audit', query),

  // ---- Ringkasan beranda ----
  ringkasan: () => get<AdminRingkasan>('/ringkasan'),
}
