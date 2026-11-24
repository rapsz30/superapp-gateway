import { ApiError, apiFetch } from '@/src/lib/api'
import type {
  CourseRecommendationResult,
  KhsCourse,
  KhsPreview,
  KhsProcessResult,
  KhsStudent,
} from '@/src/types/khs'

export const GRADE_OPTIONS = ['A', 'A-', 'A/B', 'B+', 'B', 'B-', 'B/C', 'C+', 'C', 'C-', 'C/D', 'D+', 'D', 'E', 'F']

const EMPTY_STUDENT: KhsStudent = { name: '-', nim: '-', faculty: '-', program: '-', advisor: '-', credits: '-', gpa: '-' }

function parseGpa(gpa: string): number | null {
  const value = Number(gpa.replace(',', '.'))
  return Number.isFinite(value) && value > 0 ? value : null
}

function mapPreview(preview: KhsPreview, fallback: Partial<KhsStudent>): { student: KhsStudent; courses: KhsCourse[] } {
  const rows = preview.nilai ?? []
  const courses: KhsCourse[] = rows.map((row) => {
    const grade = String(row.nilai ?? '').trim().toUpperCase()
    return {
      code: String(row.kode ?? '').trim(),
      name: String(row.nama ?? '').trim(),
      credits: typeof row.sks === 'number' && Number.isFinite(row.sks) ? row.sks : 0,
      grade: GRADE_OPTIONS.includes(grade) ? grade : '',
      semester: row.semester === '' ? undefined : row.semester,
    }
  })

  const info = preview.mahasiswa ?? {}
  const totalCredits = courses.reduce((sum, course) => sum + course.credits, 0)
  const student: KhsStudent = {
    name: info.nama || fallback.name || EMPTY_STUDENT.name,
    nim: info.nim || fallback.nim || EMPTY_STUDENT.nim,
    faculty: info.fakultas || fallback.faculty || EMPTY_STUDENT.faculty,
    program: info.prodi || fallback.program || EMPTY_STUDENT.program,
    advisor: info.dpa || EMPTY_STUDENT.advisor,
    credits: typeof info.sksKumulatif === 'number' ? `${info.sksKumulatif} SKS` : totalCredits ? `${totalCredits} SKS` : EMPTY_STUDENT.credits,
    gpa: typeof info.ipk === 'number' ? String(info.ipk).replace('.', ',') : EMPTY_STUDENT.gpa,
  }
  return { student, courses }
}

export const khsService = {
  /** Unggah PDF KHS. Backend mengekstrak teks lalu memakai LLM untuk menyusun tabel nilai. */
  async processDocument(file: File, fallback: Partial<KhsStudent> = {}): Promise<KhsProcessResult> {
    const form = new FormData()
    form.append('file', file)
    const response = await apiFetch<{ ok?: boolean; preview?: KhsPreview; warning?: string; error?: string }>(
      '/api/matkul-recommender/khs/upload',
      { method: 'POST', body: form },
    )
    if (!response.ok || !response.preview) throw new ApiError(response.error || 'KHS tidak dapat diproses.', 422)
    const { student, courses } = mapPreview(response.preview, fallback)
    return { student, courses, warning: response.warning }
  },

  /** Unggah PDF panduan akademik. Hanya ekstraksi teks (tanpa LLM). */
  async extractGuide(file: File): Promise<string> {
    const form = new FormData()
    form.append('file_pdf', file)
    const response = await apiFetch<{ ok?: boolean; text?: string }>('/api/matkul-recommender/panduan/extract-upload', {
      method: 'POST',
      body: form,
    })
    const text = String(response.text ?? '').trim()
    if (!text) throw new ApiError('Teks panduan akademik kosong. Pastikan PDF bukan hasil scan.', 422)
    return text
  },

  /** Rekomendasi mata kuliah semester berikutnya (memakai LLM). */
  async recommend(student: KhsStudent, courses: KhsCourse[], guideText: string): Promise<CourseRecommendationResult> {
    return apiFetch<CourseRecommendationResult>('/api/matkul-recommender/rekomendasi', {
      method: 'POST',
      json: {
        panduan_text: guideText,
        khs: {
          mahasiswa: { nama: student.name, nim: student.nim, fakultas: student.faculty, prodi: student.program },
          nilai: courses.map((course) => ({
            kode: course.code,
            nama: course.name,
            sks: course.credits,
            nilai: course.grade,
            semester: course.semester ?? '',
          })),
          ringkasan: { ipk: parseGpa(student.gpa) },
        },
      },
    })
  },
}
