import type { ReactNode } from 'react'
import { MatkulShell } from '@/components/matkul/matkul-shell'

export default function MatkulLayout({ children }: { children: ReactNode }) {
  return <MatkulShell>{children}</MatkulShell>
}
