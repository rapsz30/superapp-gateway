'use client'
import { createContext, useContext, useState } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { Avatar, Button, Flex, Layout, Menu, Result, Tag, Typography, type MenuProps } from 'antd'
import { BarChartOutlined, CheckSquareOutlined, HistoryOutlined, HomeOutlined, LogoutOutlined, MenuFoldOutlined, MenuUnfoldOutlined, ProfileOutlined, SettingOutlined, TeamOutlined } from '@ant-design/icons'
import { useCurrentUser } from '@/src/hooks/use-current-user'
import { BrandLogo, BrandedLoading } from '@/components/brand'
import { authService, type AuthUser } from '@/src/services/auth-service'

const { Header, Sider, Content } = Layout

const PEMBIMBING = [
  { key: '/dosen/tinjau', label: 'Rencana studi', icon: <ProfileOutlined /> },
  { key: '/dosen/bimbingan', label: 'Mahasiswa bimbingan', icon: <TeamOutlined /> },
  { key: '/dosen/riwayat', label: 'Riwayat keputusan', icon: <HistoryOutlined /> },
]
const TUGAS_AKHIR = [
  { key: '/dosen/judul', label: 'Judul perlu ditinjau', icon: <CheckSquareOutlined /> },
  { key: '/dosen/judul/riwayat', label: 'Riwayat tugas akhir', icon: <HistoryOutlined /> },
]
const KAPRODI = [
  { key: '/dosen/pembimbing-ta', label: 'Pembimbing TA', icon: <TeamOutlined /> },
  { key: '/dosen/tema-judul', label: 'Tema judul', icon: <BarChartOutlined /> },
  { key: '/dosen/prodi', label: 'Pengajuan rencana studi', icon: <ProfileOutlined /> },
  { key: '/dosen/analitik', label: 'Analitik AlurKerja', icon: <BarChartOutlined /> },
]
const LABEL_PERAN: Record<string, string> = { dosen_pa: 'Dosen PA', kaprodi: 'Kaprodi', kajur: 'Kajur', dekan: 'Dekan', superadmin: 'Superadmin' }

const DosenContext = createContext<AuthUser | null>(null)

/** Pengguna yang sedang masuk di area dosen/pengelola (selalu ada di bawah DosenShell). */
export function useDosen(): AuthUser {
  const user = useContext(DosenContext)
  if (!user) throw new Error('useDosen harus dipakai di dalam DosenShell')
  return user
}

export function DosenShell({ children }: { children: React.ReactNode }) {
  const { user, loading } = useCurrentUser()
  const pathname = usePathname()
  const router = useRouter()
  const [collapsed, setCollapsed] = useState(false)

  if (loading) return <div className="admin-loading"><BrandedLoading message="Memuat sesi pengguna..." /></div>

  const pa = !!user?.roles.includes('dosen_pa')
  const kaprodi = !!user?.roles.includes('kaprodi')
  const pengelola = !!user?.roles.some((role) => ['superadmin', 'kajur', 'dekan'].includes(role))
  if (!user || (!pa && !kaprodi && !pengelola)) {
    return <Result status="403" title="Tidak ada akses" subTitle="Halaman ini untuk dosen pembimbing, kaprodi, dan pengelola program studi." extra={<Button type="primary" href="/beranda">Kembali ke beranda</Button>} />
  }

  const menu: MenuProps['items'] = [
    ...((pa || kaprodi) ? [{ type: 'group' as const, key: 'judul', label: 'Tugas akhir', children: TUGAS_AKHIR }] : []),
    ...(pa ? [{ type: 'group' as const, key: 'pa', label: 'Pembimbing akademik', children: PEMBIMBING }] : []),
    ...((kaprodi || pengelola) ? [{ type: 'group' as const, key: 'kp', label: 'Pengelola program studi', children: KAPRODI.filter((item) => item.key !== '/dosen/pembimbing-ta' || kaprodi) }] : []),
  ]
  const halaman = [...TUGAS_AKHIR, ...PEMBIMBING, ...KAPRODI].find((item) => pathname === item.key || pathname.startsWith(`${item.key}/`))
  const judul = halaman?.label ?? (pathname.startsWith('/dosen/pengajuan/') ? 'Detail pengajuan' : 'Ruang dosen')
  const terlarang = (!pa && !kaprodi && pathname.startsWith('/dosen/judul')) || (!pa && PEMBIMBING.some((i) => pathname.startsWith(i.key))) || (!kaprodi && pathname.startsWith('/dosen/pembimbing-ta')) || (!kaprodi && !pengelola && KAPRODI.some((i) => pathname.startsWith(i.key)))

  function keluar() {
    authService.logout()
    router.push('/login')
  }

  return (
    <DosenContext.Provider value={user}>
      <Layout className="admin-layout">
        <Sider trigger={null} collapsible collapsed={collapsed} onCollapse={setCollapsed} breakpoint="lg" collapsedWidth={0} width={230} theme="light">
          <div className="admin-brand"><BrandLogo variant="mark" className="admin-brand-logo admin-brand-logo-mark" />{!collapsed && <span className="admin-brand-name">Ruang dosen</span>}</div>
          <Menu mode="inline" selectedKeys={halaman ? [halaman.key] : []} items={menu} onClick={({ key }) => router.push(key)} />
          <div className="admin-sider-bottom">
            {kaprodi && <Link href="/admin/beranda"><SettingOutlined /> Kelola prodi</Link>}
            <Link href="/beranda"><HomeOutlined /> Kembali ke beranda</Link>
            <Button className="admin-logout" type="text" danger icon={<LogoutOutlined />} onClick={keluar}>Keluar</Button>
          </div>
        </Sider>
        <Layout>
          <Header className="admin-header">
            <Button className="admin-menu-trigger" type="text" aria-label="Buka atau tutup menu" icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />} onClick={() => setCollapsed(!collapsed)} />
            <div className="admin-header-title"><Typography.Text strong>{judul}</Typography.Text><Typography.Text type="secondary">Ruang kerja dosen</Typography.Text></div>
            <Flex align="center" gap={8}>
              <Avatar size="small">{(user.full_name ?? user.email)[0]}</Avatar>
              <Typography.Text className="dosen-nama" ellipsis>{user.full_name ?? user.email}</Typography.Text>
              {user.roles.map((r) => <Tag key={r}>{LABEL_PERAN[r] ?? r}</Tag>)}
            </Flex>
          </Header>
          <Content className="admin-content">
            <div className="admin-content-heading"><Typography.Title level={3} className="admin-page-title">{judul}</Typography.Title></div>
            {terlarang ? <Result status="403" title="Bukan peran Anda" subTitle="Halaman ini tidak tersedia untuk peran Anda." /> : children}
          </Content>
        </Layout>
      </Layout>
    </DosenContext.Provider>
  )
}
