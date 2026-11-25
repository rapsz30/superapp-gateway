export type AcademicTarget = 'high' | 'ontime' | 'graduate'

// Target akademik dipakai di sisi klien untuk menandai nilai yang masih di bawah batas minimum.
export const academicTargets = [
  { id: 'high' as const, title: 'Akademik tinggi', description: 'Mengejar hasil terbaik dan menjaga peluang meraih peringkat cumlaude', minimum: 'A/B' },
  { id: 'ontime' as const, title: 'Lulus tepat waktu', description: 'Menyeimbangkan capaian nilai dan penyelesaian mata kuliah sesuai kurikulum.', minimum: 'B' },
  { id: 'graduate' as const, title: 'Fokus memenuhi syarat lulus', description: 'Memprioritaskan penyelesaian persyaratan akademik untuk menuntaskan studi.', minimum: 'C+' },
]

// Bobot nilai skala 4.0 (pedoman akademik UII), sama dengan tabel di layanan Matkul.
export const GRADE_POINTS: Record<string, number> = {
  A: 4, 'A-': 3.75, 'A/B': 3.5, 'B+': 3.25, B: 3, 'B-': 2.75, 'B/C': 2.5, 'C+': 2.25, C: 2, 'C-': 1.75, 'C/D': 1.5, 'D+': 1.25, D: 1, E: 0, F: 0,
}
