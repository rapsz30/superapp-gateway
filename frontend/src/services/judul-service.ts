import { apiFetch } from '@/src/lib/api'

export interface ThesisReference {
  sitasi: string
  link: string
}

export interface ThesisPerson {
  id: string
  nama_lengkap: string
  nim: string | null
}

export interface ThesisAdvisorOption {
  id: string
  nama_lengkap: string
}

export interface ThesisRecommendation {
  judul: string
  tema: string
  deskripsi: string
  metodologi: string
  keywords: string[]
  referensi: ThesisReference[]
}

export interface ThesisSubmission {
  id: string
  status: 'diajukan' | 'disetujui' | 'dibatalkan'
  tahap: 'tinjau' | 'perbaikan' | 'selesai'
  mode: 'alurkerja' | 'lokal'
  topik: string
  judul: string
  tema: string
  deskripsi: string
  metodologi: string
  keywords: string[]
  referensi: ThesisReference[]
  catatan: string | null
  jumlah_revisi: number
  mahasiswa: ThesisPerson | null
  pembimbing: ThesisPerson | null
  prodi: { id: string; kode: string; nama: string } | null
  diajukan_pada: string
  diputuskan_pada: string | null
}

export interface ThesisMine {
  pembimbing: ThesisPerson | null
  pengajuan: ThesisSubmission | null
  riwayat: { id: string; topik: string; dibuat: string; rekomendasi: ThesisRecommendation[] }[]
}

export interface ThesisRecommendationResult {
  id: string
  topik: string
  rekomendasi: ThesisRecommendation[]
  memakai_nilai: boolean
}

export interface ThesisSubmissionInput {
  topik: string
  judul: string
  tema: string
  deskripsi: string
  metodologi: string
  keywords: string[]
  referensi: ThesisReference[]
}

/** Satu pesan brainstorm. `kandidat_id` kosong berarti obrolan umum, selain itu pembahasan kandidat tersebut. */
export interface ThesisChatMessage {
  id: string
  peran: 'mahasiswa' | 'asisten'
  isi: string
  kandidat_id: string | null
  saran: string[]
  usulan: Omit<ThesisRecommendation, 'referensi'> | null
  versi_id: string | null
  dibuat: string
}

export interface ThesisCandidate extends ThesisRecommendation {
  id: string
  disimpan: boolean
  versi_dari: string | null
}

export interface ThesisChat {
  id: string
  topik: string
  pesan: ThesisChatMessage[]
  kandidat: ThesisCandidate[]
}

export interface ThesisChatSummary {
  id: string
  topik: string
  diubah: string
  jumlah_kandidat: number
  jumlah_disimpan: number
}

export interface ThesisRecommendationSummary {
  id: string
  topik: string
  dibuat: string
  jumlah_rekomendasi: number
}

export interface PaginatedResult<T> {
  data: T[]
  total: number
  halaman: number
  ukuran: number
}

const BASE = '/api/identity'
const OBROLAN = `${BASE}/judul/obrolan`

function normalizeRecommendation(item: Partial<ThesisRecommendation>): ThesisRecommendation {
  return {
    judul: item.judul ?? '',
    tema: item.tema ?? '',
    deskripsi: item.deskripsi ?? '',
    metodologi: item.metodologi ?? '',
    keywords: Array.isArray(item.keywords) ? item.keywords : [],
    referensi: Array.isArray(item.referensi) ? item.referensi : [],
  }
}

export const judulService = {
  async tema(): Promise<string[]> {
    const result = await apiFetch<{ data?: string[] }>(`${BASE}/judul/tema`)
    return Array.isArray(result.data) ? result.data : []
  },

  async daftarPembimbing(): Promise<ThesisAdvisorOption[]> {
    const result = await apiFetch<{ data?: ThesisAdvisorOption[] }>(`${BASE}/judul/pembimbing`)
    return Array.isArray(result.data) ? result.data : []
  },

  async saya(): Promise<ThesisMine> {
    return apiFetch<ThesisMine>(`${BASE}/judul/saya`)
  },

  async daftarRiwayat(halaman = 1, ukuran = 5): Promise<PaginatedResult<ThesisRecommendationSummary>> {
    return apiFetch<PaginatedResult<ThesisRecommendationSummary>>(`${BASE}/judul/riwayat?halaman=${halaman}&ukuran=${ukuran}`)
  },

  async rekomendasi(minat: string): Promise<ThesisRecommendationResult> {
    const result = await apiFetch<{ id: string; topik: string; rekomendasi?: Partial<ThesisRecommendation>[]; memakai_nilai?: boolean }>(`${BASE}/judul/rekomendasi`, {
      method: 'POST',
      json: { minat },
    })
    return {
      id: result.id,
      topik: result.topik,
      rekomendasi: (result.rekomendasi ?? []).map(normalizeRecommendation),
      memakai_nilai: !!result.memakai_nilai,
    }
  },

  async ajukan(input: ThesisSubmissionInput & { pembimbing_id: string }): Promise<ThesisSubmission> {
    return apiFetch<ThesisSubmission>(`${BASE}/pengajuan-judul`, { method: 'POST', json: input })
  },

  async ubah(id: string, input: ThesisSubmissionInput): Promise<ThesisSubmission> {
    return apiFetch<ThesisSubmission>(`${BASE}/pengajuan-judul/${id}`, { method: 'PUT', json: input })
  },

  async batalkan(id: string): Promise<ThesisSubmission> {
    return apiFetch<ThesisSubmission>(`${BASE}/pengajuan-judul/${id}/batalkan`, { method: 'POST' })
  },

  async daftarObrolan(halaman = 1, ukuran = 5): Promise<PaginatedResult<ThesisChatSummary>> {
    return apiFetch<PaginatedResult<ThesisChatSummary>>(`${OBROLAN}?halaman=${halaman}&ukuran=${ukuran}`)
  },
  obrolan: (id: string) => apiFetch<ThesisChat>(`${OBROLAN}/${id}`),
  mulaiObrolan: (input: { pesan: string } | { dari_rekomendasi: string }) => apiFetch<ThesisChat>(OBROLAN, { method: 'POST', json: input }),
  kirimPesan: (id: string, isi: string, kandidatId: string | null) => apiFetch<ThesisChat>(`${OBROLAN}/${id}/pesan`, { method: 'POST', json: { isi, kandidat_id: kandidatId } }),
  buatKandidat: (id: string) => apiFetch<ThesisChat>(`${OBROLAN}/${id}/kandidat`, { method: 'POST' }),
  simpanKandidat: (id: string, kandidatId: string, disimpan: boolean) => apiFetch<ThesisChat>(`${OBROLAN}/${id}/kandidat/${kandidatId}`, { method: 'PATCH', json: { disimpan } }),
  simpanVersi: (id: string, pesanId: string) => apiFetch<ThesisChat>(`${OBROLAN}/${id}/versi`, { method: 'POST', json: { pesan_id: pesanId } }),

  async getRecommendations(interests: string): Promise<ThesisRecommendation[]> {
    return (await this.rekomendasi(interests)).rekomendasi
  },
}
