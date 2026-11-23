import type { Metadata } from 'next'
import { LoginView } from '@/components/login-view'

export const metadata: Metadata = {
  title: 'Masuk — Student Gateway',
  description: 'Masuk ke Student Gateway untuk mengakses layanan akademik Anda.',
}

export default function LoginPage() {
  return <LoginView />
}
