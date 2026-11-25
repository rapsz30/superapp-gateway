import type { Metadata } from 'next'
import { cookies } from 'next/headers'
import { LanguageProvider, type Language } from '@/components/language-provider'
import './globals.css'

export const metadata: Metadata = {
  title: 'Student Gateway — Ruang Belajar Akademik',
  description: 'Satu akun untuk semua layanan akademik dan rekomendasi belajar Anda.',
}

export default async function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const cookieStore = await cookies()
  const savedLanguage = cookieStore.get('student-gateway-language')?.value
  const initialLanguage: Language = savedLanguage === 'en' ? 'en' : 'id'

  return <html lang={initialLanguage}><body><LanguageProvider initialLanguage={initialLanguage}>{children}</LanguageProvider></body></html>
}
