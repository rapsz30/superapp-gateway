'use client'
import { useMemo, useState } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { App, Avatar, Breadcrumb, Button, Dropdown, Layout, Menu, Result, Spin, Tag, Typography } from 'antd'
import { ApartmentOutlined, AuditOutlined, DashboardOutlined, HomeOutlined, MenuFoldOutlined, MenuUnfoldOutlined, LogoutOutlined, TeamOutlined } from '@ant-design/icons'
import { useCurrentUser } from '@/src/hooks/use-current-user'
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
  if (loading) return <div className="admin-loading"><Spin size="large" /></div>
  if (!user || !allowed) return <Result status="403" title="Tidak ada akses" subTitle="Halaman ini untuk superadmin, dekan, kajur, dan kaprodi." extra={<Button type="primary" href="/beranda">Kembali ke beranda</Button>} />
  async function keluar() { try { await authService.logout() } finally { message.success('Anda sudah keluar.'); router.push('/login') } }
  return <StrukturProvider isSuper={isSuper}><Layout className="admin-layout"><Sider trigger={null} collapsible collapsed={collapsed} onCollapse={setCollapsed} breakpoint="lg" collapsedWidth={0} theme="light"><div className="admin-brand">{collapsed ? 'SG' : 'Student Gateway'}</div><Menu mode="inline" selectedKeys={[current.key]} items={visibleItems} onClick={({ key }) => router.push(key)} /><div className="admin-sider-bottom"><Link href="/beranda"><HomeOutlined /> {!collapsed && 'Kembali ke beranda'}</Link><Button className="admin-logout" type="text" danger icon={<LogoutOutlined />} onClick={keluar}>{!collapsed && 'Keluar'}</Button></div></Sider><Layout><Header className="admin-header"><Button type="text" icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />} onClick={() => setCollapsed(!collapsed)} /><Typography.Text strong>{current.label}</Typography.Text><Dropdown menu={{ items: [{ key: 'logout', label: 'Keluar', icon: <LogoutOutlined />, danger: true, onClick: keluar }] }}><Button type="text"><Avatar size="small">{user.full_name?.[0] ?? user.email[0]}</Avatar> {user.full_name ?? user.email} <Tag>{user.roles.join(', ')}</Tag></Button></Dropdown></Header><Content className="admin-content"><Breadcrumb items={[{ title: 'Admin' }, { title: current.label }]} /><Typography.Title level={3}>{current.label}</Typography.Title>{pathname === '/admin/audit' && !isSuper ? <Result status="403" title="Hanya superadmin" subTitle="Hanya superadmin yang dapat melihat jejak audit." /> : children}</Content></Layout></Layout></StrukturProvider>
}
