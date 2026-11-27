import type { Metadata } from 'next'
import './admin.css'
import { AntdProvider } from '@/components/admin/antd-provider'
import { AdminShell } from '@/components/admin/admin-shell'

export const metadata: Metadata = {
  title: { default: 'Administrasi', template: '%s | Student Gateway' },
  description: 'Panel administrasi akademik Student Gateway.',
  robots: { index: false, follow: false },
}

export default function AdminLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <AntdProvider><AdminShell>{children}</AdminShell></AntdProvider>
}
