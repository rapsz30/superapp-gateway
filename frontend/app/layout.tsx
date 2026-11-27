import type { Metadata, Viewport } from 'next'
import { cookies } from 'next/headers'
import { LanguageProvider, type Language } from '@/components/language-provider'
import './globals.css'

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL || 'https://superapp.ahlanapp.cloud'),
  title: {
    default: 'Student Gateway | Layanan Akademik Terpadu',
    template: '%s | Student Gateway',
  },
  description: 'Student Gateway menyediakan akses terpadu ke layanan akademik, rencana studi, rekomendasi mata kuliah, dan tugas akhir mahasiswa.',
  applicationName: 'Student Gateway',
  keywords: ['Student Gateway', 'layanan akademik', 'rencana studi', 'tugas akhir', 'mahasiswa'],
  referrer: 'strict-origin-when-cross-origin',
  formatDetection: { telephone: false, date: false, address: false, email: false },
  icons: {
    icon: [{ url: '/brand/student-gateway-icon.svg', type: 'image/svg+xml' }],
    apple: [{ url: '/apple-icon.png', type: 'image/png', sizes: '512x512' }],
  },
  openGraph: {
    type: 'website',
    locale: 'id_ID',
    siteName: 'Student Gateway',
    title: 'Student Gateway | Layanan Akademik Terpadu',
    description: 'Akses terpadu ke layanan akademik, rencana studi, rekomendasi mata kuliah, dan tugas akhir mahasiswa.',
    url: '/',
    images: [{ url: '/brand/student-gateway-og.png', width: 1200, height: 630, type: 'image/png', alt: 'Student Gateway — layanan akademik terpadu' }],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Student Gateway | Layanan Akademik Terpadu',
    description: 'Akses terpadu ke layanan akademik dan rekomendasi belajar mahasiswa.',
    images: ['/brand/student-gateway-og.png'],
  },
  robots: { index: false, follow: false, googleBot: { index: false, follow: false } },
}

export const viewport: Viewport = {
  themeColor: '#0D2E6E',
  colorScheme: 'light',
}

export default async function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const cookieStore = await cookies()
  const savedLanguage = cookieStore.get('student-gateway-language')?.value
  const initialLanguage: Language = savedLanguage === 'en' ? 'en' : 'id'

  return <html lang={initialLanguage}><body><LanguageProvider initialLanguage={initialLanguage}>{children}</LanguageProvider></body></html>
}
