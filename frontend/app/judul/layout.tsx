import type { ReactNode } from 'react'
import { MatkulShell } from '@/components/matkul/matkul-shell'

export default function JudulLayout({ children }: { children: ReactNode }) {
  return <MatkulShell module="judul">{children}</MatkulShell>
}
