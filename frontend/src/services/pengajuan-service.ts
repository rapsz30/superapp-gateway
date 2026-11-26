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
  mahasiswa: { id: string; nama_lengkap: string; nim: string | null } | null
  dpa: { id: string; nama_lengkap: string } | null
  prodi: { id: string; kode: string; nama: string } | null
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

export interface CourseGrade {
  kode: string
  nama: string
  sks: number | null
  nilai: string
  status: 'lulus' | 'bersyarat' | 'tidak_lulus'
}

/** Ringkasan nilai dari KHS terbaru milik mahasiswa. `semester` 0 = semester tidak terbaca di KHS. */
export interface AcademicSummary {
  ringkasan: {
    ipk: number | null
    sks_lulus: number
    sks_total: number
    jumlah_mk: number
    perhatian: CourseGrade[]
    distribusi: { nilai: string; jumlah: number }[]
    per_semester: { semester: number; ip: number | null; sks: number; mk: CourseGrade[] }[]
  } | null
  sumber: { pengajuan_id: string; semester_target: number; diajukan_pada: string } | null
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

  /** Pengajuan terakhir milik seorang mahasiswa (server mengurutkan dari yang terbaru). */
  async findLatest(studentId: string): Promise<Submission | null> {
    const hasil = await apiFetch<{ data: Submission[] }>(`${BASE}?mahasiswa_id=${encodeURIComponent(studentId)}&ukuran=1`)
    const ringkas = hasil.data[0]
    return ringkas ? this.get(ringkas.id) : null
  },

  /** Riwayat pengajuan milik seorang mahasiswa, terbaru lebih dulu (tanpa isi rencana). */
  async history(studentId: string): Promise<Submission[]> {
    return (await apiFetch<{ data: Submission[] }>(`${BASE}?mahasiswa_id=${encodeURIComponent(studentId)}&ukuran=10`)).data
  },

  academicSummary(): Promise<AcademicSummary> {
    return apiFetch<AcademicSummary>(`${BASE}/ringkasan-saya`)
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
