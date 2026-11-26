'use client'

import type { ReactNode } from 'react'
import { useState } from 'react'
import { Award, BookOpen, ChevronDown, ChevronLeft, ChevronRight, FileText, Home, ListChecks, LogOut, Menu, Settings, ShieldCheck, UserRound, X } from 'lucide-react'
import { usePathname, useRouter } from 'next/navigation'
import { AppContent } from '@/components/app-content'
import { useLanguage } from '@/components/language-provider'
import { useCurrentUser } from '@/src/hooks/use-current-user'
import { authService } from '@/src/services/auth-service'

const navItems = [
  { label: 'Beranda', icon: Home },
  { label: 'Judul Tugas Akhir', icon: FileText },
  { label: 'Mata Kuliah', icon: BookOpen },
  { label: 'Micro-Credential', icon: Award },
]

export function MatkulShell({ children, module = 'matkul' }: { children: ReactNode; module?: 'matkul' | 'judul' }) {
  const router = useRouter()
  const pathname = usePathname()
  const { user, loading } = useCurrentUser()
  const { language, setLanguage, t } = useLanguage()
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [profileOpen, setProfileOpen] = useState(false)
  const [languageOpen, setLanguageOpen] = useState(false)

  if (loading && !user) {
    return <div className="app app-sidebar-collapsed"><main className="main"><div className="page-content"><div className="processing-state"><strong>Memuat sesi pengguna...</strong></div></div></main></div>
  }

  if (!user) return null

  const isMatkul = pathname.startsWith('/matkul/')
  const isJudul = pathname.startsWith('/judul/')
  const isPengajuan = pathname.startsWith('/matkul/pengajuan')
  const isJudulRekomendasi = pathname.startsWith('/judul/rekomendasi')
  const isJudulPengajuan = pathname.startsWith('/judul/pengajuan')
  const profileName = user.full_name || user.email || 'Mahasiswa'
  const navigate = (path: string) => { setMobileOpen(false); router.push(path) }
  const selectSection = (item: string) => navigate(item === 'Mata Kuliah' ? '/matkul/beranda' : item === 'Judul Tugas Akhir' ? '/judul/beranda' : '/beranda')
  const logout = () => { authService.logout(); router.push('/login') }

  return <div className={`app ${collapsed ? 'app-sidebar-collapsed' : ''}`}>
    <aside className={`sidebar ${mobileOpen ? 'sidebar-open' : ''} ${collapsed ? 'sidebar-collapsed' : ''}`}>
      <div className="sidebar-top"><div className="brand"><div className="brand-mark"><BookOpen /></div><span>Student<br />Gateway</span></div><button className="icon-button mobile-close" onClick={() => setMobileOpen(false)} aria-label="Tutup menu"><X /></button></div>
      <div className="menu-label">{t('Menu')}</div>
      <nav className="nav-list" aria-label="Navigasi utama">
        {navItems.map(({ label, icon: Icon }, index) => <div key={label}>
          {index === 1 && <div className="menu-label nav-section">{t('Rekomendasi')}</div>}
          <button className={`nav-item ${label === 'Mata Kuliah' && isMatkul || label === 'Judul Tugas Akhir' && isJudul || label === 'Beranda' && !isMatkul && !isJudul ? 'active' : ''}`} onClick={() => selectSection(label)} title={collapsed ? t(label) : undefined} aria-label={collapsed ? t(label) : undefined}><Icon /><span>{t(label)}</span></button>
        </div>)}
      </nav>
      {user.roles.some((role) => ['dosen_pa', 'kaprodi', 'superadmin', 'dekan', 'kajur'].includes(role)) && <a className="nav-item" href="/dosen" title={collapsed ? t('Ruang dosen') : undefined} aria-label={t('Ruang dosen')}><ListChecks /><span>{t('Ruang dosen')}</span></a>}
      {user.roles.some((role) => ['superadmin', 'dekan', 'kajur', 'kaprodi'].includes(role)) && <a className="nav-item" href="/admin/beranda" title={collapsed ? t('Administrasi') : undefined} aria-label={t('Administrasi')}><Settings /><span>{t('Administrasi')}</span></a>}
      <button type="button" className="logout" onClick={logout} title={collapsed ? t('Keluar') : undefined}><LogOut /><span>{t('Keluar')}</span></button>
    </aside>
    <button type="button" className="icon-button desktop-sidebar-toggle" onClick={() => setCollapsed((value) => !value)} aria-label={collapsed ? 'Perluas sidebar' : 'Ciutkan sidebar'} aria-expanded={!collapsed}>{collapsed ? <ChevronRight /> : <ChevronLeft />}</button>
    <main className="main">
      <header className="topbar">
        <button className="icon-button mobile-menu" onClick={() => setMobileOpen((value) => !value)} aria-label={mobileOpen ? 'Tutup menu' : 'Buka menu'}>{mobileOpen ? <X /> : <Menu />}</button>
        <nav className="header-breadcrumb" aria-label="Breadcrumb"><button type="button" onClick={() => navigate('/beranda')}>{t('Rekomendasi')}</button><ChevronRight aria-hidden="true" /><span aria-current="page">{isPengajuan ? 'Pengajuan KHS' : isJudulPengajuan ? 'Pengajuan judul' : isJudulRekomendasi ? 'Rekomendasi judul' : module === 'judul' ? 'Judul Tugas Akhir' : t('Mata Kuliah')}</span></nav>
        <div className="top-actions"><div className="language-wrap"><button type="button" className="language" aria-label={t('Pilih bahasa')} aria-haspopup="menu" aria-expanded={languageOpen} onClick={() => setLanguageOpen((value) => !value)}>{language.toUpperCase()} <ChevronDown /></button>{languageOpen && <div className="language-menu" role="menu" aria-label={t('Pilih bahasa')}><button type="button" role="menuitemradio" aria-checked={language === 'id'} onClick={() => { setLanguage('id'); setLanguageOpen(false) }}>Bahasa Indonesia</button><button type="button" role="menuitemradio" aria-checked={language === 'en'} onClick={() => { setLanguage('en'); setLanguageOpen(false) }}>English</button></div>}</div><div className="profile-wrap"><button className="avatar" aria-label={t('Buka profil')} aria-expanded={profileOpen} onClick={() => setProfileOpen((value) => !value)}><UserRound /></button>{profileOpen && <div className="profile-menu"><div className="profile-head"><div className="profile-avatar"><UserRound /></div><div><b>{profileName}</b><small>{user.nim || '-'}<br />{user.study_program || '-'}</small></div></div><div className="profile-divider" /><button type="button" onClick={() => navigate('/beranda')}><UserRound /> {t('Profil saya')} <ChevronDown /></button><button type="button" onClick={() => navigate('/beranda')}><ShieldCheck /> {t('Pengaturan Akun')} <ChevronDown /></button></div>}</div></div>
      </header>
      <button type="button" className={`mobile-nav-backdrop ${mobileOpen ? 'is-open' : ''}`} aria-label="Tutup menu" tabIndex={mobileOpen ? 0 : -1} onClick={() => setMobileOpen(false)} />
      <nav className={`mobile-nav ${mobileOpen ? 'is-open' : ''}`} aria-label="Navigasi utama" aria-hidden={!mobileOpen} inert={!mobileOpen}>
        {navItems.map(({ label, icon: Icon }, index) => <div key={label}>{index === 1 && <div className="mobile-nav-section">{t('Rekomendasi')}</div>}<button type="button" className={`mobile-nav-item ${label === 'Mata Kuliah' && isMatkul || label === 'Judul Tugas Akhir' && isJudul || label === 'Beranda' && !isMatkul && !isJudul ? 'active' : ''}`} onClick={() => selectSection(label)}><Icon /><span>{t(label)}</span></button></div>)}
        <button type="button" className="mobile-nav-item mobile-nav-logout" onClick={logout}><LogOut /><span>{t('Keluar')}</span></button>
      </nav>
      <AppContent>{children}</AppContent>
    </main>
  </div>
}
