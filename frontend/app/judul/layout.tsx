import type { ReactNode } from 'react'
import type { Metadata } from 'next'
import { MatkulShell } from '@/components/matkul/matkul-shell'

export const metadata: Metadata = {
  title: { default: 'Tugas Akhir', template: '%s | Student Gateway' },
  description: 'Jelajahi rekomendasi, simpan kandidat, dan ajukan topik tugas akhir melalui Student Gateway.',
  robots: { index: false, follow: false },
}

export default function JudulLayout({ children }: { children: ReactNode }) {
  return <MatkulShell module="judul">{children}</MatkulShell>
}
