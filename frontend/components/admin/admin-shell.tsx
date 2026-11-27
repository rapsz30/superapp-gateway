'use client'
import { useMemo, useState } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { App, Avatar, Breadcrumb, Button, Dropdown, Layout, Menu, Result, Tag, Typography } from 'antd'
import { ApartmentOutlined, AuditOutlined, DashboardOutlined, HomeOutlined, MenuFoldOutlined, MenuUnfoldOutlined, LogoutOutlined, SolutionOutlined, TeamOutlined } from '@ant-design/icons'
import { useCurrentUser } from '@/src/hooks/use-current-user'
import { BrandLogo, BrandedLoading } from '@/components/brand'
import { authService } from '@/src/services/auth-service'
import { StrukturProvider } from './ui'
const { Header, Sider, Content } = Layout
const MANAGERS = ['superadmin', 'dekan', 'kajur', 'kaprodi']
const items = [
  { key: '/admin/beranda', label: 'Beranda', icon: <DashboardOutlined /> },
  { key: '/admin/struktur', label: 'Struktur', icon: <ApartmentOutlined /> },
  { key: '/admin/orang', label: 'Orang & akun', icon: <TeamOutlined /> },
  { key: '/admin/audit', label: 'Jejak audit', icon: <AuditOutlined />, superOnly: true },
]
export function AdminShell({ children }: { children: React.ReactNode }) {
  const { user, loading } = useCurrentUser(); const pathname = usePathname(); const router = useRouter(); const { message } = App.useApp(); const [collapsed, setCollapsed] = useState(false)
  const isSuper = !!user?.roles.includes('superadmin'); const allowed = !!user && user.roles.some((role) => MANAGERS.includes(role)); const visibleItems = useMemo(() => items.filter((item) => !item.superOnly || isSuper).map(({ superOnly: _superOnly, ...item }) => item), [isSuper]); const current = visibleItems.find((item) => pathname.startsWith(item.key)) ?? visibleItems[0]
  if (loading) return <div className="admin-loading"><BrandedLoading message="Memuat sesi pengguna..." /></div>
  if (!user || !allowed) return <Result status="403" title="Tidak ada akses" subTitle="Halaman ini untuk superadmin, dekan, kajur, dan kaprodi." extra={<Button type="primary" href="/beranda">Kembali ke beranda</Button>} />
  async function keluar() { try { await authService.logout() } finally { message.success('Anda sudah keluar.'); router.push('/login') } }
  return <StrukturProvider isSuper={isSuper}><Layout className="admin-layout"><Sider trigger={null} collapsible collapsed={collapsed} onCollapse={setCollapsed} breakpoint="lg" collapsedWidth={0} theme="light"><div className="admin-brand"><BrandLogo variant={collapsed ? 'mark' : 'horizontal'} className={collapsed ? 'admin-brand-logo admin-brand-logo-mark' : 'admin-brand-logo'} /></div><Menu mode="inline" selectedKeys={[current.key]} items={visibleItems} onClick={({ key }) => router.push(key)} /><div className="admin-sider-bottom">{user.roles.some((role) => role === 'dosen_pa' || role === 'kaprodi') && <Link href="/dosen"><SolutionOutlined /> {!collapsed && 'Ruang dosen'}</Link>}<Link href="/beranda"><HomeOutlined /> {!collapsed && 'Kembali ke beranda'}</Link><Button className="admin-logout" type="text" danger icon={<LogoutOutlined />} onClick={keluar}>{!collapsed && 'Keluar'}</Button></div></Sider><Layout><Header className="admin-header"><Button className="admin-menu-trigger" type="text" aria-label="Buka atau tutup menu" icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />} onClick={() => setCollapsed(!collapsed)} /><div className="admin-header-title"><Typography.Text strong>{current.label}</Typography.Text><Typography.Text type="secondary">Panel administrasi akademik</Typography.Text></div><Dropdown menu={{ items: [{ key: 'logout', label: 'Keluar', icon: <LogoutOutlined />, danger: true, onClick: keluar }] }}><Button type="text" className="admin-account-button"><Avatar size="small">{user.full_name?.[0] ?? user.email[0]}</Avatar><span className="admin-account-name">{user.full_name ?? user.email}</span><Tag>{user.roles.join(', ')}</Tag></Button></Dropdown></Header><Content className="admin-content"><div className="admin-content-heading"><Breadcrumb items={[{ title: 'Admin' }, { title: current.label }]} /><Typography.Title level={3} className="admin-page-title">{current.label}</Typography.Title></div>{pathname === '/admin/audit' && !isSuper ? <Result status="403" title="Hanya superadmin" subTitle="Hanya superadmin yang dapat melihat jejak audit." /> : children}</Content></Layout></Layout></StrukturProvider>
}
