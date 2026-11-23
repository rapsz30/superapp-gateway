export type AcademicTarget = 'high' | 'ontime' | 'graduate'

export const studentRecord = {
  name: 'Vivi Zalzabilah ZI',
  nim: '23523230',
  faculty: 'Teknologi Industri',
  program: 'Informatika',
  advisor: '[Nama DPA]',
  credits: '122 SKS',
  gpa: '3,81',
}

export const courseGrades = [
  { code: 'SIF101', name: 'Pemikiran Desain', credits: 4, grade: 'A' },
  { code: 'SIF102', name: 'Fundamen Matematika', credits: 6, grade: 'A-' },
  { code: 'SIF103', name: 'Fundamen Informatika', credits: 3, grade: 'A' },
  { code: 'SIF104', name: 'Logika Pemrograman', credits: 3, grade: 'A/B' },
  { code: 'SIF201', name: 'Matematika Lanjut', credits: 6, grade: 'A' },
  { code: 'SIF202', name: 'Fundamen Pengembangan Aplikasi', credits: 6, grade: 'B+' },
  { code: 'SIF203', name: 'Algoritme dan Struktur Data', credits: 5, grade: 'A/B' },
  { code: 'SIF204', name: 'Rekayasa Perangkat Lunak', credits: 3, grade: 'A-' },
  { code: 'SIF301', name: 'Sistem dan Jaringan Komputer', credits: 6, grade: 'A' },
  { code: 'SIF302', name: 'Pengembangan Aplikasi Berbasis Web', credits: 6, grade: 'A-' },
]

export const academicTargets = [
  { id: 'high' as const, title: 'Akademik tinggi', description: 'Mengejar hasil terbaik dan menjaga peluang meraih peringkat cumlaude', minimum: 'A/B' },
  { id: 'ontime' as const, title: 'Lulus tepat waktu', description: 'Menyeimbangkan capaian nilai dan penyelesaian mata kuliah sesuai kurikulum.', minimum: 'B' },
  { id: 'graduate' as const, title: 'Fokus memenuhi syarat lulus', description: 'Memprioritaskan penyelesaian persyaratan akademik untuk menuntaskan studi.', minimum: 'C+' },
]

export const recommendations = {
  required: [
    { name: 'Tugas Akhir', code: 'SIF705', credits: '8 SKS', note: 'Wajib diambil untuk menyelesaikan studi.' },
    { name: 'Karya Ilmiah', code: 'SIF706', credits: '5 SKS', note: 'Wajib diambil untuk menyelesaikan studi.' },
  ],
  attention: [
    { name: 'Matematika Lanjut', code: 'SIF201', credits: '6 SKS', note: 'Nilai C/D belum memenuhi ketentuan. Mengulang mata kuliah ini dapat meningkatkan IPK Anda.' },
    { name: 'Fundamen Sains Data', code: 'SIF403', credits: '4 SKS', note: 'Nilai C/D belum memenuhi ketentuan. Mengulang mata kuliah ini dapat meningkatkan IPK Anda.' },
    { name: 'Grafika dan Multimedia', code: 'SIF404', credits: '3 SKS', note: 'Nilai C/D belum memenuhi ketentuan. Mengulang mata kuliah ini dapat meningkatkan IPK Anda.' },
  ],
  target: [
    { name: 'Fundamen Pengembangan Aplikasi', code: 'SIF705', grade: 'C' },
    { name: "Bahasa Arab Alquran", code: 'SIF706', grade: 'C' },
  ],
}
