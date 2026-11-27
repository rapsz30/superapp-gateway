import type { Metadata } from 'next'
import { LoginView } from '@/components/login-view'

export const metadata: Metadata = {
  title: 'Masuk',
  description: 'Masuk ke Student Gateway untuk mengakses layanan akademik, rencana studi, rekomendasi mata kuliah, dan tugas akhir.',
  alternates: { canonical: '/login' },
  robots: { index: false, follow: false },
}

export default function LoginPage() {
  return <LoginView />
}
