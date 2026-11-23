import type { KhsMockResponse } from '@/src/types/khs'

export const mockKhsResponse: KhsMockResponse = {
  student: {
    name: 'Vivi Zalzabilah ZI',
    nim: '23523230',
    faculty: 'Teknologi Industri',
    program: 'Informatika',
    advisor: '[Nama DPA]',
    credits: '119 SKS',
    gpa: '2,67',
  },
  courses: [
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
  ],
}
