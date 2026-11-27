export interface KhsCourse {
  code: string
  name: string
  credits: number
  grade: string
  semester?: string | number
}

export interface KhsStudent {
  name: string
  nim: string
  faculty: string
  program: string
  advisor: string
  credits: string
  gpa: string
}

export interface NonCourseActivity {
  name: string
  group: string
  year: string
  grade: string
}

/** Hasil ekstraksi KHS dari backend (POST /api/matkul-recommender/khs/upload). */
export interface KhsPreviewRow {
  kode?: string
  nama?: string
  sks?: number
  nilai?: string
  semester?: string | number
}

export interface KhsPreview {
  mahasiswa?: {
    nama?: string | null
    nim?: string | null
    fakultas?: string | null
    prodi?: string | null
    dpa?: string | null
    sksKumulatif?: number | null
    ipk?: number | null
    semester?: string | number | null
  }
  nilai?: KhsPreviewRow[]
}

export interface KhsProcessResult {
  student: KhsStudent
  courses: KhsCourse[]
  warning?: string
  /** Sidik berkas KHS di server, dikirim lagi saat meminta rekomendasi. */
  fingerprint?: string
}

export interface GradeEvaluation {
  kode: string
  nama: string
  nilai: string
  mutu: string
  status_lulus: string
  lulus: boolean
  saran: string
}

export interface SemesterRecommendation {
  kode: string
  nama: string
  sks: number | null
  alasan: string
  jenis: 'ulang' | 'baru'
}

/** Panduan akademik aktif (GET /api/identity/akademik/konteks). */
export interface GuideInfo {
  panduanId: string | null
  version: number | null
  title: string | null
  effectiveFrom: string | null
  program: string
  faculty: string | null
  advisorName: string | null
  panduanPribadi: boolean
  prodiTerbuka: boolean
}

/** Dasar rekomendasi: versi panduan yang dipakai server saat menyusun hasil. */
export interface RecommendationGuideRef {
  id: string
  versi: number
  judul: string
  pribadi?: boolean
  prodi: { id: string; kode: string; nama: string }
}

/** Hasil POST /api/matkul-recommender/rekomendasi. */
export interface CourseRecommendationResult {
  panduan?: RecommendationGuideRef | null
  pembimbing_akademik?: { id: string; nama_lengkap: string; email: string | null } | null
  peringatan?: string[]
  semester_target: number
  ringkasan: string
  evaluasi_nilai: GradeEvaluation[]
  rekomendasi_semester_depan: SemesterRecommendation[]
}
