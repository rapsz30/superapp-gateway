import type { Metadata } from 'next'
// Tata letak sidebar sama dengan area admin.
import '../admin/admin.css'
import { AntdProvider } from '@/components/admin/antd-provider'
import { DosenShell } from '@/components/dosen/dosen-shell'

export const metadata: Metadata = {
  title: 'Ruang dosen — Student Gateway',
  robots: { index: false, follow: false },
}

export default function DosenLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <AntdProvider><DosenShell>{children}</DosenShell></AntdProvider>
}
