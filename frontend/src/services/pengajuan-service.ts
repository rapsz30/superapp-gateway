import { apiFetch } from '@/src/lib/api'

export type SubmissionStatus = 'diajukan' | 'disetujui' | 'ditolak' | 'revisi' | 'dibatalkan'
export type SubmissionStage = 'ekstraksi' | 'periksa' | 'rekomendasi' | 'tinjau' | 'revisi' | 'selesai'

export interface SubmissionStep {
  kunci: string
  label: string
  keadaan: 'selesai' | 'aktif' | 'menunggu' | 'galat'
  keterangan: string
}

export interface Submission {
  id: string
  status: SubmissionStatus
  tahap: SubmissionStage
  langkah: SubmissionStep[]
  pesan_galat: string | null
  mode: 'alurkerja' | 'lokal'
  semester_target: number
  dpa: { id: string; nama_lengkap: string } | null
  panduan: { versi: number; versi_aktif_sekarang: number | null }
  catatan_dpa: string | null
  jumlah_revisi: number
  diajukan_pada: string
  diputuskan_pada: string | null
  /** Hasil langkah "baca KHS" (tanpa nama). */
  hasil_bacaan?: { ipk?: number | null; sks_lulus?: number | null; mk_ulang?: string[]; keyakinan?: number; nim_cocok?: boolean }
  /** Rencana studi resmi hasil proses. */
  rencana?: {
    rencana_mk?: { kode: string; nama: string; sks: number | null; alasan: string }[]
    total_sks?: number
    alasan?: string
    peringatan?: string[]
  } | null
}

export const STATUS_LABEL: Record<SubmissionStatus, string> = {
  diajukan: 'Sedang diproses',
  disetujui: 'Disetujui pembimbing akademik',
  revisi: 'Perlu revisi',
  ditolak: 'Ditolak',
  dibatalkan: 'Dibatalkan',
}

const BASE = '/api/identity/pengajuan'

export const pengajuanService = {
  /**
   * Mulai pengajuan: unggah KHS asli dan semester tujuan. Seluruh langkah (baca KHS, rekomendasi, tinjauan
   * pembimbing akademik) dijalankan proses AlurKerja di server; hasil di layar sebelumnya hanya pratinjau.
   */
  submit(file: File, semester: number): Promise<Submission> {
    const form = new FormData()
    form.append('berkas', file)
    form.append('semester_target', String(semester))
    return apiFetch<Submission>(BASE, { method: 'POST', body: form })
  },

  /** Pengajuan yang masih berjalan milik pengguna (memulihkan tampilan setelah muat ulang). */
  async findOpen(): Promise<Submission | null> {
    const hasil = await apiFetch<{ data: Submission[] }>(`${BASE}?status=diajukan&ukuran=1`)
    const ringkas = hasil.data[0]
    return ringkas ? this.get(ringkas.id) : null
  },

  get(id: string): Promise<Submission> {
    return apiFetch<Submission>(`${BASE}/${id}`)
  },

  /** Mahasiswa menyatakan hasil bacaan KHS sudah benar (langkah "Periksa"). */
  confirmCheck(id: string): Promise<Submission> {
    return apiFetch<Submission>(`${BASE}/${id}/periksa`, { method: 'POST' })
  },

  cancel(id: string): Promise<Submission> {
    return apiFetch<Submission>(`${BASE}/${id}/batalkan`, { method: 'POST' })
  },
}
