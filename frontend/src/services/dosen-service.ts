import { apiFetch } from '@/src/lib/api'
import { adminService, qs, type Bimbingan, type Orang, type Page } from '@/src/services/admin-service'
import type { Submission } from '@/src/services/pengajuan-service'

const BASE = '/api/identity'
const UKURAN = 200

/** Ambil semua halaman sebuah daftar. */
async function semua<T>(ambil: (halaman: number) => Promise<Page<T>>): Promise<T[]> {
  const hasil: T[] = []
  for (let halaman = 1; ; halaman++) {
    const { data, total } = await ambil(halaman)
    hasil.push(...data)
    if (data.length === 0 || hasil.length >= total) return hasil
  }
}

const daftarPengajuan = (filter: { dpa_id?: string; prodi_id?: string }) =>
  semua<Submission>((halaman) => apiFetch<Page<Submission>>(`${BASE}/pengajuan${qs({ ...filter, halaman, ukuran: UKURAN })}`))

export const dosenService = {
  /** Pengajuan mahasiswa yang pembimbing akademiknya adalah dosen ini. */
  pengajuanBimbingan: (dosenId: string) => daftarPengajuan({ dpa_id: dosenId }),

  /** Pengajuan satu program studi (pemantauan kaprodi). */
  pengajuanProdi: (prodiId: string) => daftarPengajuan({ prodi_id: prodiId }),

  ambil: (id: string) => apiFetch<Submission>(`${BASE}/pengajuan/${id}`),

  /** Keputusan pembimbing akademik; server meneruskannya ke AlurKerja. */
  putuskan: (id: string, keputusan: 'setuju' | 'revisi', catatan?: string) =>
    apiFetch<Submission>(`${BASE}/pengajuan/${id}/keputusan`, {
      method: 'POST',
      json: { keputusan, catatan: catatan?.trim() || null },
    }),

  async mahasiswaBimbingan(dosenId: string): Promise<{ bimbingan: Bimbingan; mahasiswa: Orang | null }[]> {
    const daftar = await semua((halaman) =>
      adminService.daftarBimbingan({ dosen_id: dosenId, aktif: true, halaman, ukuran: UKURAN }))
    return Promise.all(daftar.map(async (bimbingan) => ({
      bimbingan,
      mahasiswa: await adminService.ambilOrang(bimbingan.mahasiswa_id).catch(() => null),
    })))
  },
}
