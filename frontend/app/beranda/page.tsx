'use client'

import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Settings, ArrowLeft, Award, BookOpen, Brain, Sprout, CheckCircle2, ChevronDown, ChevronLeft, ChevronRight, ChevronUp, Clock3, Download, ExternalLink, FileText, Home, ListChecks, Loader2, LogOut, Menu, PenLine, Printer, RefreshCw, ShieldCheck, Sparkles, UserRound, X } from 'lucide-react'
import { AppContent } from '@/components/app-content'
import { CourseRecommendation } from '@/components/course-recommendation'
import { AssessmentResults } from '@/components/assessment-results'
import { ProfileView } from '@/components/profile-view'
import { AccountSettingsView } from '@/components/account-settings-view'
import { useLanguage } from '@/components/language-provider'
import { useCurrentUser } from '@/src/hooks/use-current-user'
import { errorMessage } from '@/src/lib/api'
import { authService } from '@/src/services/auth-service'
import { judulService, type ThesisRecommendation } from '@/src/services/judul-service'
import {
  microcredService,
  type AnswerPayload,
  type AssessmentQuestion,
  type AssessmentResult,
  type AssessmentStart,
  type QuestionOption,
  type Track,
} from '@/src/services/microcred-service'

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

function Sidebar({ active, onSelect, open, onClose, collapsed, onToggle, onLogout, showAdmin }: { showAdmin?: boolean; active: string; onSelect: (item: string) => void; open: boolean; onClose: () => void; collapsed: boolean; onToggle: () => void; onLogout: () => void }) {
  const { t } = useLanguage()
  return <>
    <aside id="student-sidebar" className={`sidebar ${open ? 'sidebar-open' : ''} ${collapsed ? 'sidebar-collapsed' : ''}`}>
      <div className="sidebar-top"><Brand /><button className="icon-button mobile-close" onClick={onClose} aria-label="Tutup menu"><X /></button></div>
      <div className="menu-label">{t('Menu')}</div>
      <nav className="nav-list">{navItems.map(({ label, icon: Icon }, index) => <div key={label}>
        {index === 1 && <div className="menu-label nav-section">{t('Rekomendasi')}</div>}
        <button className={`nav-item ${active === label ? 'active' : ''}`} onClick={() => { onSelect(label); onClose() }} title={collapsed ? t(label) : undefined} aria-label={collapsed ? t(label) : undefined}><Icon /><span>{t(label)}</span></button>
      </div>)}</nav>
      {showAdmin && <a className="nav-item" href="/admin/beranda" title={collapsed ? t('Administrasi') : undefined} aria-label={t('Administrasi')}><Settings /><span>{t('Administrasi')}</span></a>}
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

type AssessmentStage = 'tracks' | 'introduction' | 'theory' | 'processing' | 'results'

const trackColors = ['blue', 'lavender', 'mint', 'peach']
const trackImages = [
  'https://hebbkx1anhila5yf.public.blob.vercel-storage.com/backend_engineer-oXkb2OiGynHKE2yS547OIKldLrhbZO.png',
  'https://hebbkx1anhila5yf.public.blob.vercel-storage.com/cyber_security-FOXhXBLinDTZ4s6OoWVqogh84nmoOH.png',
  'https://hebbkx1anhila5yf.public.blob.vercel-storage.com/data_analytics.jpg-QxcbQjAK3WzgfjuLbS1FQwsDONNqnW.webp',
  'https://hebbkx1anhila5yf.public.blob.vercel-storage.com/frontend_engineer-Prf6N95a4lQjklHBto7UaWmxXqNTZu.png',
]

function MicroView({ studentName, onReturnToHome }: { studentName: string; onReturnToHome: () => void }) {
  const [stage, setStage] = useState<AssessmentStage>('tracks')
  const [tracks, setTracks] = useState<Track[]>([])
  const [loadingTracks, setLoadingTracks] = useState(true)
  const [selectedTrack, setSelectedTrack] = useState<Track | null>(null)
  const [assessment, setAssessment] = useState<AssessmentStart | null>(null)
  const [starting, setStarting] = useState(false)
  const [progressPct, setProgressPct] = useState(0)
  const [result, setResult] = useState<AssessmentResult | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    microcredService
      .tracks()
      .then((list) => {
        if (active) setTracks(list)
      })
      .catch((caught) => {
        if (active) setError(errorMessage(caught, 'Gagal memuat daftar track.'))
      })
      .finally(() => {
        if (active) setLoadingTracks(false)
      })
    return () => {
      active = false
    }
  }, [])

  async function handleStart() {
    if (!selectedTrack || starting) return
    setStarting(true)
    setError('')
    try {
      const started = await microcredService.start(selectedTrack.slug)
      setAssessment(started)
      setStage('theory')
    } catch (caught) {
      setError(errorMessage(caught, 'Gagal memulai asesmen.'))
    } finally {
      setStarting(false)
    }
  }

  async function handleAbandon() {
    const id = assessment?.assessment_id
    setAssessment(null)
    setStage('introduction')
    if (id) {
      try {
        await microcredService.abandon(id)
      } catch {
        // Abaikan bila assessment sudah tidak aktif
      }
    }
  }

  async function handleSubmit(responses: AnswerPayload[]) {
    if (!assessment) return
    setError('')
    setProgressPct(10)
    setStage('processing')
    document.querySelector<HTMLElement>('.main')?.scrollTo({ top: 0 })

    try {
      await microcredService.submit(assessment.assessment_id, responses)
      for (let attempt = 0; attempt < 60; attempt += 1) {
        const st = await microcredService.status(assessment.assessment_id)
        setProgressPct(Math.max(15, Math.round(st.overall_progress ?? 0)))
        if (st.status === 'completed') {
          const finalResult = await microcredService.result(assessment.assessment_id)
          setResult(finalResult)
          setStage('results')
          return
        }
        if (st.status === 'failed') {
          throw new Error('Pemrosesan asesmen di server gagal. Silakan coba lagi.')
        }
        await new Promise((resolve) => window.setTimeout(resolve, 2000))
      }
      throw new Error('Waktu tunggu pemrosesan asesmen habis. Silakan muat ulang atau coba lagi.')
    } catch (caught) {
      setError(errorMessage(caught, 'Gagal mengirim jawaban asesmen.'))
      setStage('theory')
    }
  }

  if (stage === 'introduction' && selectedTrack) {
    return (
      <AssessmentIntroduction
        track={selectedTrack}
        starting={starting}
        error={error}
        onBack={() => { setError(''); setStage('tracks') }}
        onStart={handleStart}
      />
    )
  }

  if (stage === 'theory' && assessment) {
    return (
      <TheoryAssessment
        assessment={assessment}
        error={error}
        onBack={handleAbandon}
        onSubmit={handleSubmit}
      />
    )
  }

  if (stage === 'processing') {
    return (
      <div className="page-content micro-page">
        <div className="workflow-card">
          <div className="processing-state">
            <Loader2 className="spin" />
            <strong>Menilai jawaban & menyiapkan rekomendasi kursus...</strong>
            <small>Progres pemrosesan AI: {progressPct}%</small>
          </div>
        </div>
      </div>
    )
  }

  if (stage === 'results' && result && selectedTrack) {
    return (
      <AssessmentResults
        result={result}
        trackName={selectedTrack.name}
        studentName={studentName}
        onReturnToHome={onReturnToHome}
      />
    )
  }

  return (
    <div className="page-content micro-page">
      <div className="view-title micro-title">
        <div>
          <h1>Temukan jalur belajar yang tepat</h1>
          <p>Selesaikan asesmen, lalu AI akan merekomendasikan kursus yang sesuai dengan tingkat kemampuan Anda saat ini.</p>
        </div>
        <div className="hero-art mini"><span></span><span></span><span></span></div>
      </div>
      <div className="section-heading"><h2>Pilih track</h2></div>
      {error && <p className="form-error" role="alert">{error}</p>}
      {loadingTracks ? (
        <div className="processing-state"><Loader2 className="spin" /><strong>Memuat daftar track...</strong></div>
      ) : (
        <div className="track-grid">
          {tracks.map((track, idx) => (
            <article className="track-card" key={track.slug}>
              <div className={`track-art ${trackColors[idx % trackColors.length]}`}>
                <img src={trackImages[idx % trackImages.length]} alt="" />
              </div>
              <div className="track-content">
                <h3>{track.name}</h3>
                <p>{track.description || 'Ukur kompetensi Anda dan dapatkan rekomendasi kursus terarah.'}</p>
                <div className="tags">
                  <span>{track.question_count} pertanyaan</span>
                  <span>15 menit</span>
                </div>
                <button
                  type="button"
                  className="primary full"
                  onClick={() => { setSelectedTrack(track); setError(''); setStage('introduction') }}
                >
                  Mulai asesmen
                </button>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  )
}

function AssessmentIntroduction({
  track,
  starting,
  error,
  onBack,
  onStart,
}: {
  track: Track
  starting: boolean
  error: string
  onBack: () => void
  onStart: () => void
}) {
  const assessmentTypes = [
    { title: 'Tes Teori', description: 'Pertanyaan pilihan ganda untuk mengukur pemahaman Anda terhadap konsep-konsep dasar.', icon: ListChecks },
    { title: 'Esai', description: 'Pertanyaan tertulis untuk menilai kemampuan analisis dan cara Anda menjelaskan konsep.', icon: PenLine },
    { title: 'Profil', description: 'Tes singkat untuk mengetahui preferensi Anda dalam memilih micro-credential.', icon: UserRound },
  ]
  return (
    <div className="page-content assessment-page">
      <button type="button" className="back-link" onClick={onBack}><ArrowLeft /> Kembali pilih track</button>
      <div className="assessment-heading"><h1>Siap memulai asesmen?</h1><p>Lengkapi rangkaian asesmen berikut untuk mengukur kesiapan Anda pada track yang dipilih.</p></div>
      <div className="selected-track-banner"><div><span>Track yang dipilih</span><strong>{track.name}</strong></div><span className="track-status"><CheckCircle2 /> Siap dimulai</span></div>
      <div className="assessment-meta">
        <div><Clock3 /><span><b>15 menit</b><small>Estimasi waktu</small></span></div>
        <div><ListChecks /><span><b>{track.question_count} pertanyaan</b><small>Seluruh tes</small></span></div>
      </div>
      <div className="assessment-section-heading"><h2>Rangkaian asesmen</h2><p>Kerjakan dengan teliti dan pastikan Anda memahami setiap instruksi.</p></div>
      <div className="assessment-type-grid">{assessmentTypes.map(({ title, description, icon: Icon }, index) => <article className="assessment-type-card" key={title}><div className="assessment-type-number">{index + 1}</div><div className="assessment-type-icon"><Icon /></div><div><h3>{title}</h3><p>{description}</p></div></article>)}</div>
      {error && <p className="form-error" role="alert">{error}</p>}
      <button type="button" className="primary assessment-start" onClick={onStart} disabled={starting}>
        {starting ? 'Menyiapkan soal...' : 'Mulai Asesmen'}
      </button>
    </div>
  )
}

function normalizeOptions(raw: unknown): QuestionOption[] {
  if (!Array.isArray(raw)) return []
  return raw
    .map((opt, i) => {
      if (typeof opt === 'string') return { id: String.fromCharCode(65 + i), text: opt }
      if (opt && typeof opt === 'object') {
        const rec = opt as Record<string, unknown>
        const id = String(rec.id ?? rec.key ?? String.fromCharCode(65 + i))
        const text = String(rec.text ?? rec.label ?? rec.value ?? id)
        return { id, text }
      }
      return null
    })
    .filter((item): item is QuestionOption => item !== null)
}

function TheoryAssessment({
  assessment,
  error,
  onBack,
  onSubmit,
}: {
  assessment: AssessmentStart
  error: string
  onBack: () => void
  onSubmit: (responses: AnswerPayload[]) => void
}) {
  const questions = assessment.questions
  const [current, setCurrent] = useState(0)
  const [mcAnswers, setMcAnswers] = useState<Record<string, string>>({})
  const [textAnswers, setTextAnswers] = useState<Record<string, string>>({})
  const [multiAnswers, setMultiAnswers] = useState<Record<string, string[]>>({})
  const [projectCounts, setProjectCounts] = useState<Record<string, number>>({})
  const [secondsLeft, setSecondsLeft] = useState(15 * 60)
  const [showExitDialog, setShowExitDialog] = useState(false)

  useEffect(() => {
    const timer = window.setInterval(() => setSecondsLeft((value) => Math.max(0, value - 1)), 1000)
    return () => window.clearInterval(timer)
  }, [])

  const q: AssessmentQuestion | undefined = questions[current]
  if (!q) return null

  const total = questions.length
  const isLast = current === total - 1
  const minuteLabel = String(Math.floor(secondsLeft / 60)).padStart(2, '0')
  const secondLabel = String(secondsLeft % 60).padStart(2, '0')

  const captures = Array.isArray(q.metadata?.captures) ? (q.metadata?.captures as string[]) : []
  const acceptedValues = Array.isArray(q.metadata?.accepted_values) ? (q.metadata?.accepted_values as string[]) : []
  const opts = normalizeOptions(q.options)

  const isEssay = q.question_type === 'essay'
  const isProfile = q.question_type === 'profile'
  const isProjectCountProfile = isProfile && captures.includes('project_count')
  const isMultiProfile = isProfile && !isProjectCountProfile && opts.length === 0 && acceptedValues.length > 0

  const category = isEssay ? 'Esai' : isProfile ? 'Profil' : 'Teori'

  const isAnswered = (index: number) => {
    const item = questions[index]
    if (!item) return false
    if (item.question_type === 'essay') return Boolean(textAnswers[item.id]?.trim())
    if (item.question_type === 'profile') {
      const itemCaps = Array.isArray(item.metadata?.captures) ? (item.metadata?.captures as string[]) : []
      const itemOpts = normalizeOptions(item.options)
      const itemAcc = Array.isArray(item.metadata?.accepted_values) ? (item.metadata?.accepted_values as string[]) : []
      if (itemCaps.includes('project_count')) {
        return projectCounts[item.id] !== undefined || (multiAnswers[item.id]?.length ?? 0) > 0
      }
      if (itemOpts.length === 0 && itemAcc.length > 0) {
        return (multiAnswers[item.id]?.length ?? 0) > 0
      }
      if (itemOpts.length > 0) return Boolean(mcAnswers[item.id])
      return Boolean(textAnswers[item.id]?.trim())
    }
    return Boolean(mcAnswers[item.id])
  }

  const theoryNumbers = questions.map((item, idx) => ({ item, num: idx + 1 })).filter((x) => x.item.question_type === 'theoretical').map((x) => x.num)
  const essayNumbers = questions.map((item, idx) => ({ item, num: idx + 1 })).filter((x) => x.item.question_type === 'essay').map((x) => x.num)
  const profileNumbers = questions.map((item, idx) => ({ item, num: idx + 1 })).filter((x) => x.item.question_type === 'profile').map((x) => x.num)

  function toggleMulti(questionId: string, val: string) {
    setMultiAnswers((prev) => {
      const currentList = prev[questionId] ?? []
      const exists = currentList.includes(val)
      return { ...prev, [questionId]: exists ? currentList.filter((v) => v !== val) : [...currentList, val] }
    })
  }

  function handleFinalSubmit() {
    const payload: AnswerPayload[] = questions.map((item) => {
      if (item.question_type === 'essay') {
        return { question_id: item.id, answer_text: (textAnswers[item.id] ?? '').trim() }
      }
      if (item.question_type === 'theoretical') {
        const picked = mcAnswers[item.id]
        return { question_id: item.id, selected_option: picked, selected_option_id: picked }
      }
      const itemCaps = Array.isArray(item.metadata?.captures) ? (item.metadata?.captures as string[]) : []
      const itemOpts = normalizeOptions(item.options)
      const itemAcc = Array.isArray(item.metadata?.accepted_values) ? (item.metadata?.accepted_values as string[]) : []
      if (itemCaps.includes('project_count')) {
        const ctx = multiAnswers[item.id] ?? []
        return {
          question_id: item.id,
          project_count: projectCounts[item.id] ?? 0,
          selected_options: ctx,
          project_contexts: ctx,
        }
      }
      if (itemOpts.length === 0 && itemAcc.length > 0) {
        const vals = multiAnswers[item.id] ?? []
        return { question_id: item.id, selected_options: vals, answer_text: vals.join(', ') }
      }
      if (itemOpts.length > 0) {
        const picked = mcAnswers[item.id]
        return { question_id: item.id, selected_option: picked, selected_option_id: picked }
      }
      return { question_id: item.id, answer_text: (textAnswers[item.id] ?? '').trim() }
    })
    onSubmit(payload)
  }

  return (
    <div className="page-content theory-screen">
      <div className="theory-screen-heading">
        <h1>{assessment.role.name}</h1>
        <button type="button" className="exit-assessment exit-assessment-desktop" onClick={() => setShowExitDialog(true)}><LogOut /> Keluar</button>
        <div className="mobile-assessment-toolbar">
          <div className="theory-toolbar-top">
            <div className="time-card time-card-compact"><span>Sisa waktu</span><strong><Clock3 /> {minuteLabel}:{secondLabel}</strong></div>
            <button type="button" className="exit-assessment" onClick={() => setShowExitDialog(true)}><LogOut /> Keluar</button>
          </div>
          <div className="question-nav-card question-nav-card-inline">
            <h3>Navigasi pertanyaan</h3>
            <div className="question-nav-groups">
              {theoryNumbers.length > 0 && <QuestionNavGroup label="Teori" numbers={theoryNumbers} current={current} isAnswered={isAnswered} onSelect={setCurrent} />}
              {essayNumbers.length > 0 && <QuestionNavGroup label="Esai" numbers={essayNumbers} current={current} isAnswered={isAnswered} onSelect={setCurrent} />}
              {profileNumbers.length > 0 && <QuestionNavGroup label="Profil" numbers={profileNumbers} current={current} isAnswered={isAnswered} onSelect={setCurrent} />}
            </div>
            <div className="question-legend"><span><i className="legend-empty" /> Belum dijawab</span><span><i className="legend-answered" /> Terjawab</span><span><i className="legend-current" /> Sedang dibuka</span></div>
          </div>
        </div>
      </div>

      <div className="theory-layout">
        <main className="theory-question-panel">
          <div className="theory-question-body">
            <div className="theory-question-top">
              <div>
                <b>Pertanyaan {current + 1} dari {total}</b>
                <div className="theory-progress"><span style={{ width: `${((current + 1) / total) * 100}%` }} /></div>
              </div>
              <strong>{Math.round(((current + 1) / total) * 100)}%</strong>
            </div>
            <div className="theory-tags">
              <span>{isEssay ? <PenLine /> : isProfile ? <UserRound /> : <BookOpen />} {category}</span>
              {q.difficulty && <span>{q.difficulty}</span>}
            </div>
            <h2>{q.prompt}</h2>
            <div className="theory-hint">
              <span>i</span>
              {isEssay
                ? 'Jelaskan dengan kata-kata Anda sendiri. Susun jawaban secara runtut dan jelaskan alasan teknisnya.'
                : isProjectCountProfile || isMultiProfile
                  ? 'Pilih semua yang sesuai dengan pengalaman Anda.'
                  : 'Pilih satu jawaban yang paling tepat.'}
            </div>

            {isProjectCountProfile ? (
              <div className="essay-answer">
                <label htmlFor="project-count-input">Jumlah proyek yang pernah Anda kerjakan</label>
                <input
                  id="project-count-input"
                  type="number"
                  min={0}
                  max={50}
                  value={projectCounts[q.id] ?? 0}
                  onChange={(event) => setProjectCounts((prev) => ({ ...prev, [q.id]: Math.max(0, Number(event.target.value) || 0) }))}
                  style={{ padding: '0.6rem 0.8rem', borderRadius: '8px', border: '1px solid #cbd5e1', maxWidth: '140px', marginBottom: '1rem' }}
                />
                {acceptedValues.length > 0 && (
                  <div className="theory-options">
                    {acceptedValues.map((val, idx) => {
                      const selected = (multiAnswers[q.id] ?? []).includes(val)
                      return (
                        <button
                          type="button"
                          className={`theory-option ${selected ? 'selected' : ''}`}
                          key={val}
                          onClick={() => toggleMulti(q.id, val)}
                        >
                          <span>{idx + 1}</span>
                          <strong>{val}</strong>
                          {selected && <CheckCircle2 />}
                        </button>
                      )
                    })}
                  </div>
                )}
              </div>
            ) : isMultiProfile ? (
              <div className="theory-options">
                {acceptedValues.map((val, idx) => {
                  const selected = (multiAnswers[q.id] ?? []).includes(val)
                  return (
                    <button
                      type="button"
                      className={`theory-option ${selected ? 'selected' : ''}`}
                      key={val}
                      onClick={() => toggleMulti(q.id, val)}
                    >
                      <span>{idx + 1}</span>
                      <strong>{val}</strong>
                      {selected && <CheckCircle2 />}
                    </button>
                  )
                })}
              </div>
            ) : opts.length > 0 ? (
              <div className="theory-options" role="radiogroup" aria-label={`Jawaban pertanyaan ${current + 1}`}>
                {opts.map((option) => (
                  <button
                    type="button"
                    role="radio"
                    aria-checked={mcAnswers[q.id] === option.id}
                    className={`theory-option ${mcAnswers[q.id] === option.id ? 'selected' : ''}`}
                    key={option.id}
                    onClick={() => setMcAnswers((prev) => ({ ...prev, [q.id]: option.id }))}
                  >
                    <span>{option.id}</span>
                    <strong>{option.text}</strong>
                    {mcAnswers[q.id] === option.id && <CheckCircle2 />}
                  </button>
                ))}
              </div>
            ) : (
              <div className="essay-answer">
                <label htmlFor="essay-response">Jawaban Anda</label>
                <textarea
                  id="essay-response"
                  value={textAnswers[q.id] ?? ''}
                  onChange={(event) => setTextAnswers((prev) => ({ ...prev, [q.id]: event.target.value }))}
                  placeholder="Tulis jawaban Anda di sini..."
                />
                <div className="essay-meta">
                  <span>{(textAnswers[q.id] ?? '').trim() ? (textAnswers[q.id] ?? '').trim().split(/\s+/).length : 0} kata</span>
                  <span><CheckCircle2 /> Jawaban tersimpan di sesi ini</span>
                </div>
              </div>
            )}
            {error && <p className="form-error" role="alert" style={{ marginTop: '0.75rem' }}>{error}</p>}
          </div>

          <div className="theory-footer">
            {current > 0 && (
              <button type="button" className="outline-button" onClick={() => setCurrent((value) => value - 1)}>
                Pertanyaan sebelumnya
              </button>
            )}
            <button
              type="button"
              className="primary"
              onClick={() => isLast ? handleFinalSubmit() : setCurrent((value) => value + 1)}
            >
              {isLast ? 'Kirim jawaban' : 'Pertanyaan berikutnya'}
            </button>
          </div>
        </main>

        <aside className="theory-sidebar">
          <div className="time-card"><span>Sisa waktu</span><strong><Clock3 /> {minuteLabel}:{secondLabel}</strong></div>
          <div className="question-nav-card">
            <h3>Navigasi pertanyaan</h3>
            {theoryNumbers.length > 0 && <QuestionNavGroup label="Teori" numbers={theoryNumbers} current={current} isAnswered={isAnswered} onSelect={setCurrent} />}
            {essayNumbers.length > 0 && <QuestionNavGroup label="Esai" numbers={essayNumbers} current={current} isAnswered={isAnswered} onSelect={setCurrent} />}
            {profileNumbers.length > 0 && <QuestionNavGroup label="Profil" numbers={profileNumbers} current={current} isAnswered={isAnswered} onSelect={setCurrent} />}
            <div className="question-legend"><span><i className="legend-empty" /> Belum dijawab</span><span><i className="legend-answered" /> Terjawab</span><span><i className="legend-current" /> Sedang dibuka</span></div>
          </div>
          <div className="autosave"><ShieldCheck /> Tersimpan selama sesi aktif</div>
        </aside>
      </div>

      {showExitDialog && (
        <div className="dialog-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setShowExitDialog(false) }}>
          <div className="confirm-dialog" role="alertdialog" aria-modal="true" aria-labelledby="exit-dialog-title" aria-describedby="exit-dialog-description" onKeyDown={(event) => { if (event.key === 'Escape') setShowExitDialog(false) }} onMouseDown={(event) => event.stopPropagation()}>
            <h2 id="exit-dialog-title">Keluar dari asesmen?</h2>
            <p id="exit-dialog-description">Asesmen akan dibatalkan dan Anda kembali ke halaman pengantar.</p>
            <div className="dialog-actions exit-dialog-actions">
              <button type="button" className="outline-button" autoFocus onClick={() => setShowExitDialog(false)}>Tetap mengerjakan</button>
              <button type="button" className="danger-button" onClick={onBack}>Keluar</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function QuestionNavGroup({ label, numbers, current, isAnswered, onSelect }: { label: string; numbers: number[]; current: number; isAnswered: (index: number) => boolean; onSelect: (value: number) => void }) {
  return <div className="question-nav-group"><b>{label}</b><div>{numbers.map((number) => {
    const index = number - 1
    const answered = isAnswered(index)
    const status = current === index ? 'Sedang dibuka' : answered ? 'Terjawab' : 'Belum dijawab'
    return <button type="button" key={number} className={current === index ? 'active' : answered ? 'answered' : ''} aria-current={current === index ? 'step' : undefined} aria-label={`Pertanyaan ${number}, ${status}`} onClick={() => onSelect(index)}>{number}</button>
  })}</div></div>
}

export default function Page() {
  const router = useRouter()
  const { user, loading } = useCurrentUser()
  const [active, setActive] = useState('Beranda')
  const [sidebarCollapsed, setSidebarCollapsed] = useState(true)

  const profile = {
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
    active === 'Profil Saya' ? <ProfileView profile={profile} /> :
    active === 'Judul Tugas Akhir' ? <ThesisView /> :
    active === 'Mata Kuliah' ? <CourseRecommendation studentFallback={{ name: profile.name, nim: profile.nim, faculty: profile.faculty, program: profile.major }} /> :
    active === 'Micro-Credential' ? <MicroView studentName={profile.name} onReturnToHome={() => setActive('Beranda')} /> :
    <HomeView onSelect={setActive} studentName={profile.name} />

  return (
    <div className={`app ${sidebarCollapsed ? 'app-sidebar-collapsed' : ''}`}>
      <Sidebar showAdmin={!!user?.roles.some((r) => ['superadmin', 'dekan', 'kajur', 'kaprodi'].includes(r))} active={active} onSelect={setActive} open={false} onClose={() => {}} collapsed={sidebarCollapsed} onToggle={() => setSidebarCollapsed((value) => !value)} onLogout={handleLogout} />
      <main className="main">
        <Topbar active={active} onSelect={setActive} onLogout={handleLogout} profile={profile} />
        <AppContent>{render}</AppContent>
      </main>
    </div>
  )
}
