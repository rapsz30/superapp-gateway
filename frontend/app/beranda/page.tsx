'use client'

import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Award, BookOpen, Brain, Sprout, ChevronDown, ChevronLeft, ChevronRight, ChevronUp, Download, ExternalLink, FileText, Home, Loader2, LogOut, Menu, Printer, RefreshCw, ShieldCheck, Sparkles, UserRound, X } from 'lucide-react'
import { AppContent } from '@/components/app-content'
import { CourseRecommendation } from '@/components/course-recommendation'
import { MicroCredentialRecommendation } from '@/components/microcred/micro-credential-recommendation'
import { ProfileView } from '@/components/profile-view'
import { AccountSettingsView } from '@/components/account-settings-view'
import { useLanguage } from '@/components/language-provider'
import { useCurrentUser } from '@/src/hooks/use-current-user'
import { errorMessage } from '@/src/lib/api'
import { authService } from '@/src/services/auth-service'
import { judulService, type ThesisRecommendation } from '@/src/services/judul-service'

const navItems = [
  { label: 'Beranda', icon: Home },
  { label: 'Judul Tugas Akhir', icon: FileText },
  { label: 'Mata Kuliah', icon: BookOpen },
  { label: 'Micro-Credential', icon: Award },
]

const topicCards = [
  { title: 'Rekomendasi Judul TA', description: 'Temukan judul penelitian yang relevan berdasarkan bidang minat dan prestasi akademik Anda.', color: 'blue', image: '/images/beranda-document.png' },
  { title: 'Rekomendasi Mata Kuliah', description: 'Dapatkan saran mata kuliah pilihan yang sesuai dengan rencana studi dan tujuan karier Anda.', color: 'violet', image: '/images/beranda-books.png' },
  { title: 'Rekomendasi Micro-Credential', description: 'Jelajahi sertifikasi singkat dan program kompetensi tambahan yang mendukung profil Anda.', color: 'orange', image: '/images/beranda-medal.png' },
]

function Brand() {
  return <div className="brand"><div className="brand-mark"><GraduationCap /></div><span>Student<br />Gateway</span></div>
}

function GraduationCap() { return <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="m3 8 9-5 9 5-9 5-9-5Z"/><path d="M7 10v5c3 2 7 2 10 0v-5M21 9v6"/></svg> }

function Sidebar({ active, onSelect, open, onClose, collapsed, onToggle, onLogout }: { active: string; onSelect: (item: string) => void; open: boolean; onClose: () => void; collapsed: boolean; onToggle: () => void; onLogout: () => void }) {
  const { t } = useLanguage()
  return <>
    <aside id="student-sidebar" className={`sidebar ${open ? 'sidebar-open' : ''} ${collapsed ? 'sidebar-collapsed' : ''}`}>
      <div className="sidebar-top"><Brand /><button className="icon-button mobile-close" onClick={onClose} aria-label="Tutup menu"><X /></button></div>
      <div className="menu-label">{t('Menu')}</div>
      <nav className="nav-list">{navItems.map(({ label, icon: Icon }, index) => <div key={label}>
        {index === 1 && <div className="menu-label nav-section">{t('Rekomendasi')}</div>}
        <button className={`nav-item ${active === label ? 'active' : ''}`} onClick={() => { onSelect(label); onClose() }} title={collapsed ? t(label) : undefined} aria-label={collapsed ? t(label) : undefined}><Icon /><span>{t(label)}</span></button>
      </div>)}</nav>
      <button type="button" className="logout" onClick={onLogout} title={collapsed ? t('Keluar') : undefined}><LogOut /><span>{t('Keluar')}</span></button>
    </aside>
    <button
      type="button"
      className="icon-button desktop-sidebar-toggle"
      onClick={onToggle}
      aria-label={collapsed ? t('Perluas sidebar') : t('Ciutkan sidebar')}
      aria-expanded={!collapsed}
      aria-controls="student-sidebar"
      title={collapsed ? t('Perluas sidebar') : t('Ciutkan sidebar')}
    >
      {collapsed ? <ChevronRight /> : <ChevronLeft />}
    </button>
  </>
}

function Topbar({
  active,
  onSelect,
  onLogout,
  profile,
}: {
  active: string
  onSelect: (item: string) => void
  onLogout: () => void
  profile: { name: string; nim: string; major: string }
}) {
  const [profileOpen, setProfileOpen] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const [languageOpen, setLanguageOpen] = useState(false)
  const { language, setLanguage, t } = useLanguage()
  return <><header className="topbar"><button className="icon-button mobile-menu" onClick={() => setMenuOpen((value) => !value)} aria-label={t(menuOpen ? 'Tutup menu' : 'Buka menu')} aria-expanded={menuOpen}>{menuOpen ? <X /> : <Menu />}</button>{['Mata Kuliah', 'Micro-Credential', 'Judul Tugas Akhir'].includes(active) ? <nav className="header-breadcrumb" aria-label="Breadcrumb"><button type="button" onClick={() => onSelect('Beranda')}>{t('Rekomendasi')}</button><ChevronRight aria-hidden="true" /><span aria-current="page">{t(active)}</span></nav> : <span className="header-breadcrumb current-page">{t(active)}</span>}<div className="top-actions"><div className="language-wrap"><button type="button" className="language" aria-label={t('Pilih bahasa')} aria-haspopup="menu" aria-expanded={languageOpen} onClick={() => setLanguageOpen((value) => !value)}>{language.toUpperCase()} <ChevronDown /></button>{languageOpen && <div className="language-menu" role="menu" aria-label={t('Pilih bahasa')}><button type="button" role="menuitemradio" aria-checked={language === 'id'} onClick={() => { setLanguage('id'); setLanguageOpen(false) }}>Bahasa Indonesia</button><button type="button" role="menuitemradio" aria-checked={language === 'en'} onClick={() => { setLanguage('en'); setLanguageOpen(false) }}>English</button></div>}</div><div className="profile-wrap"><button className="avatar" aria-label={t('Buka profil')} aria-expanded={profileOpen} onClick={() => setProfileOpen(!profileOpen)}><UserRound /></button>{profileOpen && <div className="profile-menu"><div className="profile-head"><div className="profile-avatar"><UserRound /></div><div><b>{profile.name}</b><small>{profile.nim}<br />{profile.major}</small></div></div><div className="profile-divider" /><button type="button" onClick={() => { onSelect('Profil Saya'); setProfileOpen(false) }}><UserRound /> {t('Profil saya')} <ChevronDown /></button><button type="button" onClick={() => { onSelect('Pengaturan Akun'); setProfileOpen(false) }}><ShieldCheck /> {t('Pengaturan Akun')} <ChevronDown /></button></div>}</div></div></header><button type="button" className={`mobile-nav-backdrop ${menuOpen ? 'is-open' : ''}`} aria-label="Tutup menu" tabIndex={menuOpen ? 0 : -1} onClick={() => setMenuOpen(false)} /><nav className={`mobile-nav ${menuOpen ? 'is-open' : ''}`} aria-label={t('Navigasi utama')} aria-hidden={!menuOpen} inert={!menuOpen}>{navItems.map(({ label, icon: Icon }, index) => <div key={label}>{index === 1 && <div className="mobile-nav-section">Rekomendasi</div>}<button type="button" className={`mobile-nav-item ${active === label ? 'active' : ''}`} aria-current={active === label ? 'page' : undefined} onClick={() => { onSelect(label); setMenuOpen(false) }}><Icon /><span>{t(label)}</span></button></div>)}<button type="button" className="mobile-nav-item mobile-nav-logout" onClick={onLogout}><LogOut /><span>{t('Keluar')}</span></button></nav></>
}

function HomeView({ onSelect, studentName }: { onSelect: (item: string) => void; studentName: string }) {
  const { t } = useLanguage()
  return <div className="page-content home-view"><div className="welcome"><div><h1>{t('Selamat datang kembali')}</h1><p className="welcome-copy">{t('Halo')}, {studentName}</p></div></div>
    <section className="hero"><div><h2>{t('Rencanakan studi Anda dengan lebih baik')}</h2><p>{t('Jelajahi rekomendasi judul tugas akhir, mata kuliah, dan micro-credential')}<br className="desktop-only" /> {t('yang sesuai dengan minat dan tujuanmu.')}</p></div><img className="hero-illustration" src="/images/hero-student.png" alt="" /></section>
    <div className="section-heading"><h2>{t('Mulai Eksplorasi')}</h2></div>
    <div className="topic-grid">{topicCards.map(({ title, description, color, image }, i) => <article className={`topic-card ${color}`} key={title}><div className="topic-card-copy"><h3>{t(title)}</h3><p>{t(description)}</p><button type="button" className="card-link" onClick={() => onSelect(i === 0 ? 'Judul Tugas Akhir' : i === 1 ? 'Mata Kuliah' : 'Micro-Credential')}>{t('Mulai')}</button></div><div className={`card-illustration ${color}-art`}><img src={image} alt="" /></div></article>)}</div>
  </div>
}

const topicSuggestions = [
  { title: 'Machine Learning', description: 'Saya tertarik pada klasifikasi dan prediksi data menggunakan machine learning.', prompt: 'Saya ingin mengeksplorasi ide tugas akhir tentang machine learning, terutama klasifikasi dan prediksi data.', icon: Sparkles },
  { title: 'Pertanian', description: 'Saya tertarik pada pemanfaatan teknologi untuk mengembangkan sektor pertanian.', prompt: 'Saya ingin mencari ide tugas akhir tentang teknologi di bidang pertanian.', icon: Sprout },
  { title: 'Psikologi', description: 'Saya tertarik memahami perilaku manusia melalui pendekatan teknologi dan penelitian.', prompt: 'Saya ingin mengeksplorasi ide tugas akhir yang berkaitan dengan psikologi dan teknologi.', icon: Brain },
]

function ThesisView() {
  const [input, setInput] = useState('')
  const composerRef = useRef<HTMLTextAreaElement>(null)
  useLayoutEffect(() => {
    const textarea = composerRef.current
    if (!textarea) return
    const fitToContent = () => {
      textarea.style.height = 'auto'
      textarea.style.height = `${textarea.scrollHeight}px`
    }
    fitToContent()
    window.addEventListener('resize', fitToContent)
    return () => window.removeEventListener('resize', fitToContent)
  }, [input])
  const [submittedTopic, setSubmittedTopic] = useState('')
  const [results, setResults] = useState<ThesisRecommendation[] | null>(null)
  const [isGenerating, setIsGenerating] = useState(false)
  const [error, setError] = useState('')
  const [expanded, setExpanded] = useState<Set<number>>(new Set())

  async function submitTopic(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const topic = input.trim()
    if (!topic || isGenerating) return
    setSubmittedTopic(topic)
    setError('')
    setIsGenerating(true)
    try {
      const items = await judulService.getRecommendations(topic)
      setResults(items)
      setExpanded(new Set())
    } catch (caught) {
      setError(errorMessage(caught, 'Gagal mengambil rekomendasi judul.'))
    } finally {
      setIsGenerating(false)
    }
  }

  if (results) {
    return (
      <ThesisResults
        topic={submittedTopic}
        items={results}
        onChangeTopic={() => setResults(null)}
        expanded={expanded}
        setExpanded={setExpanded}
      />
    )
  }

  return <div className="page-content thesis-chat-page"><div className="thesis-chat-header"><img className="thesis-chat-illustration" src="/images/thesis-thinking.png" alt="" width={1536} height={1024} /><h1>Topik apa yang Anda minati?</h1></div><div className="chat-suggestions">{topicSuggestions.map(({ title, description, prompt, icon: Icon }) => <button type="button" className="chat-suggestion" key={title} onClick={() => setInput(prompt)}><span className="chat-suggestion-icon"><Icon /></span><strong>{title}</strong><p>{description}</p></button>)}</div><h2 className="thesis-chat-alt" id="thesis-custom-idea">Punya ide lain?</h2><form className="chat-panel chat-composer" onSubmit={submitTopic} aria-busy={isGenerating}><textarea ref={composerRef} value={input} onChange={(event) => { setInput(event.target.value); setError('') }} placeholder="Tuliskan ide atau topik yang ingin Anda bahas..." rows={3} aria-labelledby="thesis-custom-idea" disabled={isGenerating} />{error && <p className="form-error" role="alert">{error}</p>}<div className="chat-composer-footer"><button type="submit" className="primary chat-send" disabled={isGenerating}>{isGenerating ? 'Menyiapkan rekomendasi...' : 'Cari Rekomendasi'} {isGenerating && <span className="button-loader" aria-hidden="true" />}</button></div></form></div>
}

function ThesisResults({
  topic,
  items,
  onChangeTopic,
  expanded,
  setExpanded,
}: {
  topic: string
  items: ThesisRecommendation[]
  onChangeTopic: () => void
  expanded: Set<number>
  setExpanded: React.Dispatch<React.SetStateAction<Set<number>>>
}) {
  return (
    <div className="page-content thesis-results-page">
      <div className="submitted-topic">
        <div><b>Topik yang Anda masukkan</b><p>{topic}</p></div>
        <button type="button" className="primary change-topic-button" onClick={onChangeTopic}><RefreshCw /> Ganti topik</button>
      </div>
      <div className="results-toolbar">
        <h1>{items.length} rekomendasi judul</h1>
        <div>
          <button type="button" className="outline-button" onClick={() => window.print()}><Download /> Export ke PDF</button>
          <button type="button" className="outline-button" onClick={() => window.print()}><Printer /> Cetak</button>
        </div>
      </div>
      {items.length === 0 ? (
        <div className="activity-result-empty">Tidak ada rekomendasi judul yang dihasilkan. Coba topik lain.</div>
      ) : (
        <div className="thesis-result-list">
          {items.map((item, index) => (
            <ThesisResultCard
              key={`${item.judul}-${index}`}
              item={item}
              index={index}
              expanded={expanded.has(index)}
              onToggle={() => setExpanded((current) => {
                const next = new Set(current)
                if (next.has(index)) next.delete(index)
                else next.add(index)
                return next
              })}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function ThesisResultCard({
  item,
  index,
  expanded,
  onToggle,
}: {
  item: ThesisRecommendation
  index: number
  expanded: boolean
  onToggle: () => void
}) {
  return (
    <article className={`thesis-result-card ${expanded ? 'expanded' : ''}`}>
      <div className="result-card-title">
        <span className="result-number">{index + 1}</span>
        <h2>{item.judul}</h2>
      </div>
      <p className="result-description">{item.deskripsi}</p>
      {item.keywords.length > 0 && (
        <div className="result-tags">
          {item.keywords.map((tag) => <span key={tag}>{tag}</span>)}
        </div>
      )}
      <div className={`result-details-shell ${expanded ? 'is-open' : ''}`} aria-hidden={!expanded}>
        <div className="result-details">
          {item.metodologi && (
            <>
              <h3>Metodologi</h3>
              <p style={{ whiteSpace: 'pre-line' }}>{item.metodologi}</p>
            </>
          )}
          {item.referensi.length > 0 && (
            <>
              <h3>Referensi</h3>
              <div className="reference-list">
                {item.referensi.map((ref, refIndex) => (
                  <a href={ref.link} key={`${ref.link}-${refIndex}`} target="_blank" rel="noreferrer">
                    {ref.sitasi} <ExternalLink />
                  </a>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
      {(item.metodologi || item.referensi.length > 0) && (
        <button type="button" className="result-detail-toggle" onClick={onToggle}>
          {expanded ? 'Sembunyikan detail' : 'Lihat detail'} {expanded ? <ChevronUp /> : <ChevronDown />}
        </button>
      )}
    </article>
  )
}

export default function Page() {
  const router = useRouter()
  const { user, loading } = useCurrentUser()
  const [active, setActive] = useState('Beranda')
  const [sidebarCollapsed, setSidebarCollapsed] = useState(true)
  const [profileOverride, setProfileOverride] = useState<{ email: string; name: string; nim: string; faculty: string; major: string } | null>(null)

  const profile = profileOverride ?? {
    email: user?.email ?? '',
    name: user?.full_name || user?.email || 'Mahasiswa',
    nim: user?.nim || '-',
    faculty: user?.faculty || '-',
    major: user?.study_program || '-',
  }

  function handleLogout() {
    authService.logout()
    router.push('/login')
  }

  if (loading && !user) {
    return (
      <div className="app app-sidebar-collapsed">
        <main className="main">
          <div className="page-content">
            <div className="processing-state"><Loader2 className="spin" /><strong>Memuat sesi pengguna...</strong></div>
          </div>
        </main>
      </div>
    )
  }

  const render =
    active === 'Pengaturan Akun' ? <AccountSettingsView email={profile.email} /> :
    active === 'Profil Saya' ? <ProfileView profile={profile} onChange={setProfileOverride} /> :
    active === 'Judul Tugas Akhir' ? <ThesisView /> :
    active === 'Mata Kuliah' ? <CourseRecommendation studentFallback={{ name: profile.name, nim: profile.nim, faculty: profile.faculty, program: profile.major }} /> :
    active === 'Micro-Credential' ? <MicroCredentialRecommendation studentName={profile.name} onReturnToHome={() => setActive('Beranda')} /> :
    <HomeView onSelect={setActive} studentName={profile.name} />

  return (
    <div className={`app ${sidebarCollapsed ? 'app-sidebar-collapsed' : ''}`}>
      <Sidebar active={active} onSelect={setActive} open={false} onClose={() => {}} collapsed={sidebarCollapsed} onToggle={() => setSidebarCollapsed((value) => !value)} onLogout={handleLogout} />
      <main className="main">
        <Topbar active={active} onSelect={setActive} onLogout={handleLogout} profile={profile} />
        <AppContent>{render}</AppContent>
      </main>
    </div>
  )
}
