'use client'

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'

export type Language = 'id' | 'en'

type LanguageContextValue = {
  language: Language
  setLanguage: (language: Language) => void
  t: (text: string) => string
}

const translations: Record<string, string> = {
  'Beranda': 'Home', 'Judul Tugas Akhir': 'Thesis Topics', 'Mata Kuliah': 'Courses', 'Micro-Credential': 'Micro-Credentials',
  'Rekomendasi': 'Recommendations', 'Menu': 'Menu', 'Keluar': 'Sign out', 'Perluas sidebar': 'Expand sidebar', 'Ciutkan sidebar': 'Collapse sidebar',
  'Tutup menu': 'Close menu', 'Buka menu': 'Open menu', 'Buka profil': 'Open profile', 'Selamat datang kembali': 'Welcome back',
  'Halo, Vivi Zalzabilah': 'Hello, Vivi Zalzabilah', 'Rencanakan studi Anda dengan lebih baik': 'Plan your studies with confidence',
  'Jelajahi rekomendasi judul tugas akhir, mata kuliah, dan micro-credential': 'Explore thesis topic, course, and micro-credential recommendations',
  'yang sesuai dengan minat dan tujuanmu.': 'tailored to your interests and goals.', 'Jelajahi rekomendasi': 'Explore recommendations',
  'Mulai Eksplorasi': 'Start exploring', 'Rekomendasi Judul TA': 'Thesis Topic Recommendations',
  'Temukan judul penelitian yang relevan berdasarkan bidang minat dan prestasi akademik Anda.': 'Find relevant research topics based on your interests and academic achievements.',
  'Rekomendasi Mata Kuliah': 'Course Recommendations', 'Dapatkan saran mata kuliah pilihan yang sesuai dengan rencana studi dan tujuan karier Anda.': 'Get elective course suggestions aligned with your study plan and career goals.',
  'Rekomendasi Micro-Credential': 'Micro-Credential Recommendations', 'Jelajahi sertifikasi singkat dan program kompetensi tambahan yang mendukung profil Anda.': 'Explore short certifications and additional skills programs to strengthen your profile.',
  'Mulai': 'Start', 'Profil saya': 'My profile', 'Pengaturan Akun': 'Account settings', 'Profil Saya': 'My Profile', 'Vivi Zalzabilah': 'Vivi Zalzabilah',
  'Profil mahasiswa': 'Student profile', 'Kelola informasi akademik dan identitas Anda.': 'Manage your academic and identity information.', 'Informasi pribadi': 'Personal information', 'Perbarui data profil akademik Anda.': 'Update your academic profile details.',
  'Alamat email': 'Email address', 'Email tidak dapat diubah': 'Email cannot be changed', 'Nama lengkap': 'Full name', 'Nomor Induk Mahasiswa (NIM)': 'Student ID number',
  'Fakultas': 'Faculty', 'Jurusan': 'Major', 'Simpan perubahan': 'Save changes', 'Perubahan profil berhasil disimpan.': 'Profile changes saved successfully.',
  'Pengaturan akun': 'Account settings', 'Keamanan akun': 'Account security', 'Kelola kata sandi dan keamanan akun Anda.': 'Manage your password and account security.', 'Ubah kata sandi': 'Change password', 'Tampilkan kata sandi': 'Show password', 'Sembunyikan kata sandi': 'Hide password', 'Masukkan kata sandi saat ini dan buat kata sandi baru.': 'Enter your current password and create a new one.', 'Kata sandi saat ini': 'Current password', 'Kata sandi baru': 'New password', 'Ulangi kata sandi baru': 'Repeat new password', 'Gunakan minimal 8 karakter.': 'Use at least 8 characters.', 'Simpan kata sandi': 'Save password', 'Simpan kata sandi baru': 'Save new password', 'Lupa kata sandi?': 'Forgot password?', 'Konfirmasi kata sandi baru tidak cocok.': 'The new password confirmation does not match.', 'Kata sandi berhasil diubah.': 'Password changed successfully.', 'Verifikasi alamat email': 'Verify email address', 'Masukkan email akun untuk memulai simulasi reset kata sandi.': 'Enter the account email to start the password reset simulation.', 'Lanjutkan verifikasi': 'Continue verification', 'Verifikasi email': 'Email verification', 'Dalam layanan nyata, tautan verifikasi akan dikirim ke': 'In a real service, a verification link would be sent to', 'Tidak ada email yang benar-benar dikirim. Lanjutkan untuk melihat langkah reset.': 'No email was actually sent. Continue to view the reset step.', 'Lanjutkan simulasi': 'Continue simulation', 'Gunakan email lain': 'Use another email', 'Buat kata sandi baru': 'Create a new password', 'Langkah verifikasi email simulasi selesai untuk': 'The simulated email verification step is complete for', 'Simulasi reset selesai': 'Reset simulation complete', 'Kata sandi akun tidak diubah dan tidak ada email yang dikirim.': 'The account password was not changed and no email was sent.', 'Kembali ke pengaturan akun': 'Back to account settings',
  'Topik apa yang Anda minati?': 'What topics interest you?', 'Punya ide lain?': 'Have another idea?',
  'Tuliskan ide atau topik yang ingin Anda bahas...': 'Write an idea or topic you would like to explore...',
  'Cari Rekomendasi': 'Find recommendations', 'Menyiapkan rekomendasi...': 'Preparing recommendations...',
  'Topik yang Anda masukkan': 'Your topic', 'Ganti topik': 'Change topic', '3 rekomendasi judul': '3 topic recommendations',
  'Export ke PDF': 'Export to PDF', 'Cetak': 'Print', 'Masalah': 'Problem', 'Solusi': 'Solution', 'Output': 'Outcome',
  'Metodologi': 'Methodology', 'Referensi': 'References', 'Sembunyikan detail': 'Hide details', 'Lihat detail': 'View details',
  'Temukan jalur belajar yang tepat': 'Find the right learning path',
  'Selesaikan asesmen, lalu AI akan merekomendasikan kursus yang sesuai dengan tingkat kemampuan Anda saat ini.': 'Complete the assessment and AI will recommend courses suited to your current skill level.',
  'Pilih track': 'Choose a track', '10 pertanyaan': '10 questions', '15 menit': '15 minutes', 'Mulai asesmen': 'Start assessment',
  'Kembali': 'Back', 'Lihat hasil rekomendasi': 'View recommendations', 'Simpan dan lanjut': 'Save and continue', 'Lanjut': 'Continue',
  'ID': 'Indonesian', 'EN': 'English', 'Pilih bahasa': 'Choose language', 'Bahasa': 'Language',
  'Unggah KHS': 'Upload transcript', 'Preview KHS': 'Transcript preview', 'Input dan edit nilai': 'Enter and edit grades',
  'Panduan akademik': 'Academic guide', 'Target Akademik': 'Academic goals', 'Rekomendasi mata kuliah': 'Course recommendations',
  'Pastikan file KHS Anda dalam format PDF.': 'Make sure your transcript is a PDF file.',
  'Pastikan seluruh data sudah benar sebelum melanjutkan.': 'Make sure all information is correct before continuing.',
  'Perbaiki hasil ekstraksi KHS sebelum lanjut ke rekomendasi.': 'Review the extracted transcript before continuing to recommendations.',
  'Rekomendasi disusun berdasarkan data akademik dan target Anda.': 'Recommendations are based on your academic record and goals.',
  'Informasi mahasiswa': 'Student information', 'Daftar mata kuliah': 'Course list', 'Kegiatan non-mata kuliah': 'Extracurricular activities',
  'Tambahkan nilai kegiatan di luar mata kuliah jika ada': 'Add grades for extracurricular activities, if applicable',
  'Nama kegiatan': 'Activity name', 'Kelas/Kelompok': 'Class/Group', 'Tahun (opsional)': 'Year (optional)', 'Nilai akhir': 'Final grade',
  'Pilih kegiatan': 'Choose an activity', 'Pilih nilai': 'Choose a grade', 'Tambah kegiatan': 'Add activity', 'Daftar kegiatan': 'Activity list',
  'Belum ada data.': 'No data yet.', 'Tambah mata kuliah': 'Add course', 'Mata kuliah baru': 'New course', 'Target akademik': 'Academic goal',
  'Apa prioritas studi Anda?': 'What is your study priority?', 'Lulus tepat waktu': 'Graduate on time',
  'Kembali ke beranda': 'Back to home', 'Ringkasan skor': 'Score summary', 'Skor keseluruhan': 'Overall score',
  'Analisis AI': 'AI analysis', 'Rekomendasi kursus': 'Course recommendations', 'Asesmen selesai': 'Assessment complete',
  'Hasil asesmen Anda': 'Your assessment results', 'Teori': 'Theory', 'Esai': 'Essay', 'Profil': 'Profile',
  'Asesmen micro-credential': 'Micro-credential assessment', 'Masuk': 'Sign in', 'Daftar': 'Sign up',
}

const LanguageContext = createContext<LanguageContextValue | null>(null)

export function LanguageProvider({ initialLanguage, children }: { initialLanguage: Language; children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>(initialLanguage)

  useEffect(() => {
    document.documentElement.lang = language
  }, [language])

  const setLanguage = useCallback((nextLanguage: Language) => {
    setLanguageState(nextLanguage)
    document.cookie = `student-gateway-language=${nextLanguage}; path=/; max-age=31536000; samesite=lax${location.protocol === 'https:' ? '; secure' : ''}`
  }, [])

  const value = useMemo<LanguageContextValue>(() => ({
    language,
    setLanguage,
    t: (text) => language === 'en' ? translations[text] ?? text : text,
  }), [language, setLanguage])

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>
}

export function useLanguage() {
  const context = useContext(LanguageContext)
  if (!context) throw new Error('useLanguage must be used within LanguageProvider')
  return context
}
