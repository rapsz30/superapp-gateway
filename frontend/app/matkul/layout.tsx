import type { ReactNode } from 'react'
import type { Metadata } from 'next'
import { MatkulShell } from '@/components/matkul/matkul-shell'

export const metadata: Metadata = {
  title: { default: 'Mata Kuliah', template: '%s | Student Gateway' },
  description: 'Kelola rencana studi dan temukan rekomendasi mata kuliah sesuai hasil akademik Anda.',
  robots: { index: false, follow: false },
}

export default function MatkulLayout({ children }: { children: ReactNode }) {
  return <MatkulShell>{children}</MatkulShell>
}
