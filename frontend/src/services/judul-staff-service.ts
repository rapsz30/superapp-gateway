import { apiFetch } from '@/src/lib/api'
import { qs, type Page } from '@/src/services/admin-service'
import type { ThesisPerson, ThesisSubmission } from '@/src/services/judul-service'

const BASE = '/api/identity'
const UKURAN = 100

export interface ThesisAssignmentRow {
  mahasiswa: ThesisPerson
  pembimbing: ThesisPerson | null
  judul: Pick<ThesisSubmission, 'status' | 'tahap' | 'judul' | 'tema'> | null
}

export interface ThesisAdvisorCandidate {
  id: string
  nama_lengkap: string
}

export interface ThesisThemeStat {
  tema: string
  disetujui: number
  berjalan: number
  total: number
}

export interface ThesisThemeSummary {
  prodi: { id: string; kode: string; nama: string }
  total: number
  tema: ThesisThemeStat[]
}

async function semua<T>(ambil: (halaman: number) => Promise<Page<T>>): Promise<T[]> {
  const hasil: T[] = []
  for (let halaman = 1; ; halaman += 1) {
    const halamanData = await ambil(halaman)
    hasil.push(...halamanData.data)
    if (!halamanData.data.length || hasil.length >= halamanData.total) return hasil
  }
}

export const judulStaffService = {
  pengajuan: (pembimbingId: string, status?: string) =>
    semua<ThesisSubmission>((halaman) => apiFetch<Page<ThesisSubmission>>(`${BASE}/pengajuan-judul${qs({ pembimbing_id: pembimbingId, status, halaman, ukuran: UKURAN })}`)),

  ambil: (id: string) => apiFetch<ThesisSubmission>(`${BASE}/pengajuan-judul/${id}`),

  putuskan: (id: string, keputusan: 'setuju' | 'revisi', catatan?: string) =>
    apiFetch<ThesisSubmission>(`${BASE}/pengajuan-judul/${id}/keputusan`, {
      method: 'POST',
      json: { keputusan, catatan: catatan?.trim() || null },
    }),

  daftarPembimbing: (prodiId: string) =>
    apiFetch<{ data: ThesisAdvisorCandidate[] }>(`${BASE}/pembimbing-ta/dosen${qs({ prodi_id: prodiId })}`).then((result) => result.data),

  daftarMahasiswa: (prodiId: string) =>
    semua<ThesisAssignmentRow>((halaman) => apiFetch<Page<ThesisAssignmentRow>>(`${BASE}/pembimbing-ta${qs({ prodi_id: prodiId, halaman, ukuran: UKURAN })}`)),

  tunjukPembimbing: (mahasiswaId: string, dosenId: string) =>
    apiFetch<{ pembimbing: ThesisPerson }>(`${BASE}/pembimbing-ta`, {
      method: 'PUT',
      json: { mahasiswa_id: mahasiswaId, dosen_id: dosenId },
    }),

  statistikTema: (prodiId?: string) =>
    apiFetch<{ data: ThesisThemeSummary[] }>(`${BASE}/judul/statistik-tema${qs({ prodi_id: prodiId })}`).then((result) => result.data),
}
