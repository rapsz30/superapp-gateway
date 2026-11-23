'use client'

import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { ArrowLeft, Award, BookOpen, Brain, Sprout, CheckCircle2, ChevronDown, ChevronLeft, ChevronRight, ChevronUp, Clock3, Download, ExternalLink, FileText, Home, ListChecks, LogOut, Menu, PenLine, Printer, RefreshCw, ShieldCheck, Sparkles, UserRound, X } from 'lucide-react'
import { AppContent } from '@/components/app-content'
import { CourseRecommendation } from '@/components/course-recommendation'
import { AssessmentResults } from '@/components/assessment-results'
import { ProfileView } from '@/components/profile-view'
import { AccountSettingsView } from '@/components/account-settings-view'
import { LoginView } from '@/components/login-view'
import { useLanguage } from '@/components/language-provider'

const navItems = [
  { label: 'Beranda', icon: Home },
  { label: 'Judul Tugas Akhir', icon: FileText },
  { label: 'Mata Kuliah', icon: BookOpen },
  { label: 'Micro-Credential', icon: Award }
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

function Topbar({ active, onSelect }: { active: string; onSelect: (item: string) => void }) {
  const [profileOpen, setProfileOpen] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const [languageOpen, setLanguageOpen] = useState(false)
  const { language, setLanguage, t } = useLanguage()
  return <><header className="topbar"><button className="icon-button mobile-menu" onClick={() => setMenuOpen((value) => !value)} aria-label={t(menuOpen ? 'Tutup menu' : 'Buka menu')} aria-expanded={menuOpen}>{menuOpen ? <X /> : <Menu />}</button>{['Mata Kuliah', 'Micro-Credential', 'Judul Tugas Akhir'].includes(active) ? <nav className="header-breadcrumb" aria-label="Breadcrumb"><button type="button" onClick={() => onSelect('Beranda')}>{t('Rekomendasi')}</button><ChevronRight aria-hidden="true" /><span aria-current="page">{t(active)}</span></nav> : <span className="header-breadcrumb current-page">{t(active)}</span>}<div className="top-actions"><div className="language-wrap"><button type="button" className="language" aria-label={t('Pilih bahasa')} aria-haspopup="menu" aria-expanded={languageOpen} onClick={() => setLanguageOpen((value) => !value)}>{language.toUpperCase()} <ChevronDown /></button>{languageOpen && <div className="language-menu" role="menu" aria-label={t('Pilih bahasa')}><button type="button" role="menuitemradio" aria-checked={language === 'id'} onClick={() => { setLanguage('id'); setLanguageOpen(false) }}>Bahasa Indonesia</button><button type="button" role="menuitemradio" aria-checked={language === 'en'} onClick={() => { setLanguage('en'); setLanguageOpen(false) }}>English</button></div>}</div><div className="profile-wrap"><button className="avatar" aria-label={t('Buka profil')} aria-expanded={profileOpen} onClick={() => setProfileOpen(!profileOpen)}><UserRound /></button>{profileOpen && <div className="profile-menu"><div className="profile-head"><div className="profile-avatar"><UserRound /></div><div><b>Vivi Zalzabilah</b><small>23523230<br />Informatika</small></div></div><div className="profile-divider" /><button type="button" onClick={() => { onSelect('Profil Saya'); setProfileOpen(false) }}><UserRound /> {t('Profil saya')} <ChevronDown /></button><button type="button" onClick={() => { onSelect('Pengaturan Akun'); setProfileOpen(false) }}><ShieldCheck /> {t('Pengaturan Akun')} <ChevronDown /></button></div>}</div></div></header><button type="button" className={`mobile-nav-backdrop ${menuOpen ? 'is-open' : ''}`} aria-label="Tutup menu" tabIndex={menuOpen ? 0 : -1} onClick={() => setMenuOpen(false)} /><nav className={`mobile-nav ${menuOpen ? 'is-open' : ''}`} aria-label={t('Navigasi utama')} aria-hidden={!menuOpen} inert={!menuOpen}>{navItems.map(({ label, icon: Icon }, index) => <div key={label}>{index === 1 && <div className="mobile-nav-section">Rekomendasi</div>}<button type="button" className={`mobile-nav-item ${active === label ? 'active' : ''}`} aria-current={active === label ? 'page' : undefined} onClick={() => { onSelect(label); setMenuOpen(false) }}><Icon /><span>{t(label)}</span></button></div>)}<button type="button" className="mobile-nav-item mobile-nav-logout"><LogOut /><span>Keluar</span></button></nav></>
}

function HomeView({ onSelect }: { onSelect: (item: string) => void }) {
  const { t } = useLanguage()
  return <div className="page-content home-view"><div className="welcome"><div><h1>{t('Selamat datang kembali')}</h1><p className="welcome-copy">{t('Halo, Vivi Zalzabilah')}</p></div></div>
    <section className="hero"><div><h2>{t('Rencanakan studi Anda dengan lebih baik')}</h2><p>{t('Jelajahi rekomendasi judul tugas akhir, mata kuliah, dan micro-credential')}<br className="desktop-only" /> {t('yang sesuai dengan minat dan tujuanmu.')}</p></div><img className="hero-illustration" src="/images/hero-student.png" alt="" /></section>
    <div className="section-heading"><h2>{t('Mulai Eksplorasi')}</h2></div>
    <div className="topic-grid">{topicCards.map(({ title, description, color, image }, i) => <article className={`topic-card ${color}`} key={title}><div className="topic-card-copy"><h3>{t(title)}</h3><p>{t(description)}</p><button type="button" className="card-link" onClick={() => onSelect(i === 0 ? 'Judul Tugas Akhir' : i === 1 ? 'Mata Kuliah' : 'Micro-Credential')}>{t('Mulai')}</button></div><div className={`card-illustration ${color}-art`}><img src={image} alt="" /></div></article>)}</div>
  </div>
}

const thesisResults = [
  { title: 'Aplikasi Mobile Pembelajaran Interaktif Berbasis Augmented Reality untuk Sekolah Dasar', description: 'Aplikasi ini memanfaatkan teknologi AR untuk memperkaya pengalaman belajar siswa SD melalui visualisasi 3D materi pelajaran.', tags: ['Augmented Reality', 'Flutter', 'Education Technology'], problem: 'Keterbatasan media pembelajaran konvensional.', solution: 'Integrasi AR dalam aplikasi mobile yang mudah diakses.', output: 'Aplikasi interaktif dengan modul pelajaran 3D.', methods: [['Literature Review', 'Studi literatur tentang AR dalam pendidikan, review paper, survei aplikasi.', 'Google Scholar, Zotero, Mendeley'], ['Persiapan Data', 'Pengumpulan model 3D, gambar, dan pembuatan dataset.', 'Blender, Adobe Photoshop, Google Drive'], ['Development', 'Pengembangan aplikasi dengan Flutter, plugin ARCore/ARKit, dan Firebase Cloud Firestore.', 'Flutter, ARCore/ARKit, Firebase'], ['Testing', 'Unit testing Flutter, integration testing, dan beta testing di sekolah.', 'Flutter Test, Firebase Test Lab'], ['Dokumentasi', 'Menulis laporan dan menyiapkan presentasi.', 'LaTeX, Overleaf']], references: ['Cari paper terkait ‘Augmented Reality, Flutter, Education Technology’ di Google Scholar', 'Gunakan Semantic Scholar untuk pencarian yang lebih spesifik'] },
  { title: 'Sistem Penilaian Otomatis Kegiatan Belajar Mengajar Menggunakan Machine Learning pada Aplikasi Mobile Sekolah Dasar', description: 'Sistem ini menilai tugas siswa secara otomatis melalui analisis gambar dan teks menggunakan ML, mengurangi beban guru.', tags: ['Machine Learning', 'TensorFlow Lite', 'Asesmen Pendidikan'] },
  { title: 'Platform Mobile Kegiatan Ekstrakurikuler Berbasis Gamifikasi untuk Sekolah Dasar', description: 'Platform ini memotivasi siswa SD untuk berpartisipasi dalam kegiatan ekstrakurikuler melalui elemen gamifikasi.', tags: ['Gamification', 'Flutter', 'Extracurricular Activities'] },
]

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
  const [showResults, setShowResults] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)
  const [expanded, setExpanded] = useState<Set<number>>(new Set())

  function submitTopic(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const topic = input.trim()
    if (!topic || isGenerating) return
    setSubmittedTopic(topic)
    setIsGenerating(true)
    window.setTimeout(() => {
      setIsGenerating(false)
      setShowResults(true)
      setExpanded(new Set())
    }, 700)
  }

  if (showResults) return <ThesisResults topic={submittedTopic} onChangeTopic={() => setShowResults(false)} expanded={expanded} setExpanded={setExpanded} />

  return <div className="page-content thesis-chat-page"><div className="thesis-chat-header"><img className="thesis-chat-illustration" src="/images/thesis-thinking.png" alt="" width={1536} height={1024} /><h1>Topik apa yang Anda minati?</h1></div><div className="chat-suggestions">{topicSuggestions.map(({ title, description, prompt, icon: Icon }) => <button type="button" className="chat-suggestion" key={title} onClick={() => setInput(prompt)}><span className="chat-suggestion-icon"><Icon /></span><strong>{title}</strong><p>{description}</p></button>)}</div><h2 className="thesis-chat-alt" id="thesis-custom-idea">Punya ide lain?</h2><form className="chat-panel chat-composer" onSubmit={submitTopic} aria-busy={isGenerating}><textarea ref={composerRef} value={input} onChange={(event) => setInput(event.target.value)} placeholder="Tuliskan ide atau topik yang ingin Anda bahas..." rows={3} aria-labelledby="thesis-custom-idea" disabled={isGenerating} /><div className="chat-composer-footer"><button type="submit" className="primary chat-send" disabled={isGenerating}>{isGenerating ? 'Menyiapkan rekomendasi...' : 'Cari Rekomendasi'} {isGenerating && <span className="button-loader" aria-hidden="true" />}</button></div></form></div>
}

function ThesisResults({ topic, onChangeTopic, expanded, setExpanded }: { topic: string; onChangeTopic: () => void; expanded: Set<number>; setExpanded: React.Dispatch<React.SetStateAction<Set<number>>> }) {
  return <div className="page-content thesis-results-page"><div className="submitted-topic"><div><b>Topik yang Anda masukkan</b><p>{topic}</p></div><button type="button" className="primary change-topic-button" onClick={onChangeTopic}><RefreshCw /> Ganti topik</button></div><div className="results-toolbar"><h1>3 rekomendasi judul</h1><div><button type="button" className="outline-button" onClick={() => window.print()}><Download /> Export ke PDF</button><button type="button" className="outline-button" onClick={() => window.print()}><Printer /> Cetak</button></div></div><div className="thesis-result-list">{thesisResults.map((item, index) => <ThesisResultCard key={item.title} item={item} index={index} expanded={expanded.has(index)} onToggle={() => setExpanded((current) => { const next = new Set(current); if (next.has(index)) next.delete(index); else next.add(index); return next })} />)}</div></div>
}

function ThesisResultCard({ item, index, expanded, onToggle }: { item: typeof thesisResults[number]; index: number; expanded: boolean; onToggle: () => void }) {
  return <article className={`thesis-result-card ${expanded ? 'expanded' : ''}`}><div className="result-card-title"><span className="result-number">{index + 1}</span><h2>{item.title}</h2></div><p className="result-description">{item.description}</p><div className="result-tags">{item.tags.map((tag) => <span key={tag}>{tag}</span>)}</div><div className={`result-details-shell ${expanded ? 'is-open' : ''}`} aria-hidden={!expanded}><div className="result-details">{item.methods && <><div className="result-detail-grid"><div><b>Masalah</b><p>{item.problem}</p></div><div><b>Solusi</b><p>{item.solution}</p></div><div><b>Output</b><p>{item.output}</p></div></div><h3>Metodologi</h3><ol className="method-list">{item.methods.map(([name, description, tools], methodIndex) => <li key={name}><span>{methodIndex + 1}</span><div><b>{name}</b><p>{description}</p><small>Tools: {tools}</small></div></li>)}</ol><h3>Referensi</h3><div className="reference-list">{item.references?.map((reference) => <a href="#" key={reference} onClick={(event) => event.preventDefault()}>{reference}<ExternalLink /></a>)}</div></>}</div></div><button type="button" className="result-detail-toggle" onClick={onToggle}>{expanded ? 'Sembunyikan detail' : 'Lihat detail'} {expanded ? <ChevronUp /> : <ChevronDown />}</button></article>
}

type MicroTrack = 'Backend Engineer' | 'Cyber Security' | 'Data Analyst' | 'Frontend Engineer'
type AssessmentStage = 'tracks' | 'introduction' | 'theory' | 'results'
type TheoryQuestion = { question: string; options: string[] }

const microTracks: { title: MicroTrack; description: string; color: string; image: string }[] = [
  { title: 'Backend Engineer', description: 'Pelajari pengembangan API, desain basis data, microservices, dan teknologi backend modern.', color: 'blue', image: 'https://hebbkx1anhila5yf.public.blob.vercel-storage.com/backend_engineer-oXkb2OiGynHKE2yS547OIKldLrhbZO.png' },
  { title: 'Cyber Security', description: 'Pelajari dasar keamanan, keamanan aplikasi dan jaringan, respons insiden, dan berpikir dalam arsitektur keamanan.', color: 'lavender', image: 'https://hebbkx1anhila5yf.public.blob.vercel-storage.com/cyber_security-FOXhXBLinDTZ4s6OoWVqogh84nmoOH.png' },
  { title: 'Data Analyst', description: 'Pelajari analisis data, visualisasi, SQL, Python untuk data science, serta alat seperti Pandas dan Tableau.', color: 'mint', image: 'https://hebbkx1anhila5yf.public.blob.vercel-storage.com/data_analytics.jpg-QxcbQjAK3WzgfjuLbS1FQwsDONNqnW.webp' },
  { title: 'Frontend Engineer', description: 'Asesmen kompetensi frontend yang mencakup HTML/CSS/JS, React, dan arsitektur.', color: 'peach', image: 'https://hebbkx1anhila5yf.public.blob.vercel-storage.com/frontend_engineer-Prf6N95a4lQjklHBto7UaWmxXqNTZu.png' },
]

const essayQuestions: Record<MicroTrack, TheoryQuestion[]> = {
  'Backend Engineer': [
    { question: 'Jelaskan bagaimana Anda merancang API yang aman dan mudah dikembangkan untuk sebuah aplikasi.', options: [] },
    { question: 'Jelaskan pendekatan Anda saat melakukan debugging pada layanan backend yang bermasalah.', options: [] },
    { question: 'Jelaskan pertimbangan Anda ketika memilih struktur database untuk sebuah fitur baru.', options: [] },
  ],
  'Cyber Security': [
    { question: 'Jelaskan langkah yang Anda lakukan saat menyusun respons terhadap insiden keamanan.', options: [] },
    { question: 'Jelaskan cara Anda menilai risiko keamanan pada sebuah aplikasi web.', options: [] },
    { question: 'Jelaskan strategi Anda untuk membangun kebiasaan keamanan yang baik dalam tim.', options: [] },
  ],
  'Data Analyst': [
    { question: 'Jelaskan bagaimana Anda mengubah data mentah menjadi insight yang dapat ditindaklanjuti.', options: [] },
    { question: 'Jelaskan cara Anda memastikan kualitas data sebelum membuat laporan.', options: [] },
    { question: 'Jelaskan bagaimana Anda memilih visualisasi yang tepat untuk menyampaikan sebuah temuan.', options: [] },
  ],
  'Frontend Engineer': [
    { question: 'Jelaskan pendekatan Anda untuk membuat antarmuka yang responsive dan mudah diakses.', options: [] },
    { question: 'Jelaskan cara Anda membagi komponen saat membangun halaman frontend yang kompleks.', options: [] },
    { question: 'Jelaskan langkah yang Anda lakukan untuk meningkatkan performa aplikasi web.', options: [] },
  ],
}

const theoryQuestions: Record<MicroTrack, TheoryQuestion[]> = {
  'Backend Engineer': [
    { question: 'Apa fungsi utama sebuah API dalam aplikasi backend?', options: ['Menghubungkan aplikasi dengan layanan atau data lain', 'Mengatur warna antarmuka pengguna', 'Menggantikan sistem operasi server', 'Menyimpan password di dalam kode'] },
    { question: 'Metode HTTP yang umum digunakan untuk mengambil data adalah...', options: ['POST', 'GET', 'PATCH', 'DELETE'] },
    { question: 'Apa tujuan utama penggunaan primary key dalam database?', options: ['Mengurutkan warna tabel', 'Mengidentifikasi setiap record secara unik', 'Menghapus seluruh data lama', 'Menyimpan file gambar'] },
    { question: 'Manakah yang termasuk proses server-side?', options: ['Validasi dan pemrosesan data di server', 'Mengubah ukuran ikon di browser', 'Mengatur posisi tombol dengan CSS', 'Memilih tema perangkat pengguna'] },
    { question: 'Apa manfaat utama arsitektur microservices?', options: ['Semua fitur wajib berada dalam satu file', 'Layanan dapat dikembangkan dan diskalakan secara terpisah', 'Database tidak lagi diperlukan', 'Aplikasi hanya dapat berjalan offline'] },
  ],
  'Cyber Security': [
    { question: 'Apa tujuan utama autentikasi?', options: ['Memastikan identitas pengguna', 'Menyembunyikan warna halaman', 'Menghapus seluruh log server', 'Mempercepat koneksi internet'] },
    { question: 'Apa fungsi enkripsi pada data?', options: ['Mengubah data menjadi bentuk yang sulit dibaca tanpa kunci', 'Menghapus data secara permanen', 'Membuat data selalu bersifat publik', 'Mengganti alamat IP pengguna'] },
    { question: 'Manakah contoh serangan social engineering?', options: ['Phishing melalui email palsu', 'Mengganti kabel jaringan', 'Memperbarui sistem operasi', 'Membuat backup database'] },
    { question: 'Prinsip least privilege berarti pengguna...', options: ['Mendapatkan akses minimum yang diperlukan', 'Selalu menjadi administrator', 'Tidak perlu menggunakan password', 'Boleh mengakses semua sistem'] },
    { question: 'Apa langkah awal yang tepat saat mendeteksi insiden keamanan?', options: ['Mendokumentasikan dan mengisolasi insiden sesuai prosedur', 'Menghapus semua bukti', 'Membagikan kredensial ke publik', 'Mematikan seluruh layanan tanpa analisis'] },
  ],
  'Data Analyst': [
    { question: 'Apa tujuan utama eksplorasi data?', options: ['Memahami pola, kualitas, dan karakteristik data', 'Menghapus semua nilai yang berbeda', 'Mengganti database dengan spreadsheet', 'Membuat data tanpa sumber'] },
    { question: 'SQL digunakan terutama untuk...', options: ['Mengelola dan mengambil data dari database', 'Mendesain logo aplikasi', 'Mengompresi video', 'Mengatur koneksi Bluetooth'] },
    { question: 'Median adalah...', options: ['Nilai tengah setelah data diurutkan', 'Nilai terbesar dalam data', 'Jumlah seluruh data', 'Selisih nilai minimum dan maksimum'] },
    { question: 'Visualisasi yang tepat untuk melihat tren dari waktu ke waktu adalah...', options: ['Grafik garis', 'Diagram lingkaran tunggal', 'Tabel tanpa urutan', 'Ikon status'] },
    { question: 'Apa tujuan validasi data sebelum analisis?', options: ['Memastikan data akurat, konsisten, dan siap digunakan', 'Menambah duplikasi data', 'Menghilangkan semua outlier tanpa alasan', 'Membuat hasil tidak dapat direproduksi'] },
  ],
  'Frontend Engineer': [
    { question: 'HTML berfungsi untuk...', options: ['Menyusun struktur konten halaman', 'Mengelola query database', 'Mengenkripsi password', 'Menjalankan server backend'] },
    { question: 'CSS terutama digunakan untuk...', options: ['Mengatur tampilan dan layout antarmuka', 'Menyimpan data pengguna', 'Mengirim email server', 'Membuat tabel database'] },
    { question: 'Apa kegunaan state pada aplikasi React?', options: ['Menyimpan data yang dapat berubah dan memengaruhi tampilan', 'Menggantikan semua elemen HTML', 'Menghapus kebutuhan terhadap komponen', 'Mengatur DNS domain'] },
    { question: 'Desain responsive bertujuan agar...', options: ['Tampilan menyesuaikan berbagai ukuran layar', 'Aplikasi hanya berjalan di desktop', 'Semua teks menjadi gambar', 'Server tidak memerlukan jaringan'] },
    { question: 'Apa manfaat component-based architecture?', options: ['UI dapat dibangun dari bagian yang dapat digunakan kembali', 'Semua kode harus berada di satu komponen', 'CSS tidak lagi diperlukan', 'Data otomatis menjadi terenkripsi'] },
  ],
}

function MicroView({ onReturnToHome }: { onReturnToHome: () => void }) {
  const [stage, setStage] = useState<AssessmentStage>('tracks')
  const [selectedTrack, setSelectedTrack] = useState<MicroTrack | null>(null)

  if (stage === 'introduction' && selectedTrack) return <AssessmentIntroduction track={selectedTrack} onBack={() => setStage('tracks')} onStart={() => setStage('theory')} />
  if (stage === 'theory' && selectedTrack) return <TheoryAssessment track={selectedTrack} onBack={() => setStage('introduction')} onSubmit={() => { document.querySelector<HTMLElement>('.main')?.scrollTo({ top: 0 }); setStage('results') }} />
  if (stage === 'results' && selectedTrack) return <AssessmentResults track={selectedTrack} onReturnToHome={onReturnToHome} />

  return <div className="page-content micro-page"><div className="view-title micro-title"><div><h1>Temukan jalur belajar yang tepat</h1><p>Selesaikan asesmen, lalu AI akan merekomendasikan kursus yang sesuai dengan tingkat kemampuan Anda saat ini.</p></div><div className="hero-art mini"><span></span><span></span><span></span></div></div><div className="section-heading"><h2>Pilih track</h2></div><div className="track-grid">{microTracks.map((track) => <article className="track-card" key={track.title}><div className={`track-art ${track.color}`}><img src={track.image} alt="" /></div><div className="track-content"><h3>{track.title}</h3><p>{track.description}</p><div className="tags"><span>10 pertanyaan</span><span>15 menit</span></div><button type="button" className="primary full" onClick={() => { setSelectedTrack(track.title); setStage('introduction') }}>Mulai asesmen</button></div></article>)}</div></div>
}

function AssessmentIntroduction({ track, onBack, onStart }: { track: MicroTrack; onBack: () => void; onStart: () => void }) {
  const assessmentTypes = [
    { title: 'Tes Teori', description: 'Pertanyaan pilihan ganda untuk mengukur pemahaman Anda terhadap konsep-konsep dasar.', icon: ListChecks },
    { title: 'Esai', description: 'Pertanyaan tertulis untuk menilai kemampuan analisis dan cara Anda menjelaskan konsep.', icon: PenLine },
    { title: 'Profil', description: 'Tes singkat untuk mengetahui preferensi Anda dalam memilih micro-credential.', icon: UserRound }
  ]
  return <div className="page-content assessment-page"><button type="button" className="back-link" onClick={onBack}><ArrowLeft /> Kembali pilih track</button><div className="assessment-heading"><h1>Siap memulai asesmen?</h1><p>Lengkapi rangkaian asesmen berikut untuk mengukur kesiapan Anda pada track yang dipilih.</p></div><div className="selected-track-banner"><div><span>Track yang dipilih</span><strong>{track}</strong></div><span className="track-status"><CheckCircle2 /> Siap dimulai</span></div><div className="assessment-meta"><div><Clock3 /><span><b>15 menit</b><small>Estimasi waktu</small></span></div><div><ListChecks /><span><b>10 pertanyaan</b><small>Seluruh tes</small></span></div></div><div className="assessment-section-heading"><h2>Rangkaian asesmen</h2><p>Kerjakan dengan teliti dan pastikan Anda memahami setiap instruksi.</p></div><div className="assessment-type-grid">{assessmentTypes.map(({ title, description, icon: Icon }, index) => <article className="assessment-type-card" key={title}><div className="assessment-type-number">{index + 1}</div><div className="assessment-type-icon"><Icon /></div><div><h3>{title}</h3><p>{description}</p></div></article>)}</div><button type="button" className="primary assessment-start" onClick={onStart}>Mulai Asesmen</button></div>
}

function TheoryAssessment({ track, onBack, onSubmit }: { track: MicroTrack; onBack: () => void; onSubmit: () => void }) {
  const questions = [...theoryQuestions[track], ...theoryQuestions[track]].slice(0, 10)
  const [current, setCurrent] = useState(0)
  const [answers, setAnswers] = useState<Record<number, number>>({})
  const [essayAnswers, setEssayAnswers] = useState<Record<number, string>>({})
  const [secondsLeft, setSecondsLeft] = useState(14 * 60 + 52)
  const [showExitDialog, setShowExitDialog] = useState(false)
  const isEssay = current >= 3 && current <= 5
  const question = isEssay ? essayQuestions[track][current - 3] : questions[current]
  const essayAnswer = essayAnswers[current] ?? ''
  const isLast = current === questions.length - 1
  const minuteLabel = String(Math.floor(secondsLeft / 60)).padStart(2, '0')
  const secondLabel = String(secondsLeft % 60).padStart(2, '0')
  const questionNumbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
  const isProfile = current >= 6
  const category = isEssay ? 'Esai' : isProfile ? 'Profil' : 'Teori'
  const topicTag = isEssay ? 'http-methods' : isProfile ? null : 'http-dutnz'
  const isAnswered = (index: number) => index >= 3 && index <= 5 ? Boolean(essayAnswers[index]?.trim()) : answers[index] !== undefined

  useEffect(() => {
    const timer = window.setInterval(() => setSecondsLeft((value) => Math.max(0, value - 1)), 1000)
    return () => window.clearInterval(timer)
  }, [])

  return <div className="page-content theory-screen"><div className="theory-screen-heading"><h1>{track}</h1><button type="button" className="exit-assessment exit-assessment-desktop" onClick={() => setShowExitDialog(true)}><LogOut /> Keluar</button><div className="mobile-assessment-toolbar"><div className="theory-toolbar-top"><div className="time-card time-card-compact"><span>Sisa waktu</span><strong><Clock3 /> {minuteLabel}:{secondLabel}</strong></div><button type="button" className="exit-assessment" onClick={() => setShowExitDialog(true)}><LogOut /> Keluar</button></div><div className="question-nav-card question-nav-card-inline"><h3>Navigasi pertanyaan</h3><div className="question-nav-groups"><QuestionNavGroup label="Teori" numbers={questionNumbers.slice(0, 3)} current={current} isAnswered={isAnswered} onSelect={setCurrent} /><QuestionNavGroup label="Esai" numbers={questionNumbers.slice(3, 6)} current={current} isAnswered={isAnswered} onSelect={setCurrent} /><QuestionNavGroup label="Profil" numbers={questionNumbers.slice(6)} current={current} isAnswered={isAnswered} onSelect={setCurrent} /></div><div className="question-legend"><span><i className="legend-empty" /> Belum dijawab</span><span><i className="legend-answered" /> Terjawab</span><span><i className="legend-current" /> Sedang dibuka</span></div></div></div></div><div className="theory-layout"><main className="theory-question-panel"><div className="theory-question-body"><div className="theory-question-top"><div><b>Pertanyaan {current + 1} dari 10</b><div className="theory-progress"><span style={{ width: `${((current + 1) / 10) * 100}%` }} /></div></div><strong>{Math.round(((current + 1) / 10) * 100)}%</strong></div><div className="theory-tags"><span>{isEssay ? <PenLine /> : isProfile ? <UserRound /> : <BookOpen />} {category}</span>{topicTag && <span>{topicTag}</span>}</div><h2>{question.question}</h2><div className="theory-hint"><span>i</span>{isEssay ? 'Jelaskan dengan kata-kata Anda sendiri. Susun jawaban secara runtut dan jelaskan alasan di balik setiap keputusan teknis.' : 'Pilih satu jawaban yang paling tepat.'}</div>{isEssay ? <div className="essay-answer"><label htmlFor="essay-response">Jawaban Anda</label><textarea id="essay-response" value={essayAnswer} onChange={(event) => setEssayAnswers((previous) => ({ ...previous, [current]: event.target.value }))} placeholder="Tulis jawaban Anda di sini..." /><div className="essay-meta"><span>{essayAnswer.trim() ? essayAnswer.trim().split(/\s+/).length : 0} kata</span><span><CheckCircle2 /> Jawaban tersimpan otomatis</span></div></div> : <div className="theory-options" role="radiogroup" aria-label={`Jawaban pertanyaan ${current + 1}`}>{question.options.map((option, index) => <button type="button" role="radio" aria-checked={answers[current] === index} className={`theory-option ${answers[current] === index ? 'selected' : ''}`} key={option} onClick={() => setAnswers((previous) => ({ ...previous, [current]: index }))}><span>{String.fromCharCode(65 + index)}</span><strong>{option}</strong>{answers[current] === index && <CheckCircle2 />}</button>)}</div>}</div><div className="theory-footer">{current > 0 && <button type="button" className="outline-button" onClick={() => setCurrent((value) => value - 1)}>Pertanyaan sebelumnya</button>}<button type="button" className="primary" onClick={() => isLast ? onSubmit() : setCurrent((value) => value + 1)}>{isLast ? 'Kirim jawaban' : 'Pertanyaan berikutnya'}</button></div></main><aside className="theory-sidebar"><div className="time-card"><span>Sisa waktu</span><strong><Clock3 /> {minuteLabel}:{secondLabel}</strong></div><div className="question-nav-card"><h3>Navigasi pertanyaan</h3><QuestionNavGroup label="Teori" numbers={questionNumbers.slice(0, 3)} current={current} isAnswered={isAnswered} onSelect={setCurrent} /><QuestionNavGroup label="Esai" numbers={questionNumbers.slice(3, 6)} current={current} isAnswered={isAnswered} onSelect={setCurrent} /><QuestionNavGroup label="Profil" numbers={questionNumbers.slice(6)} current={current} isAnswered={isAnswered} onSelect={setCurrent} /><div className="question-legend"><span><i className="legend-empty" /> Belum dijawab</span><span><i className="legend-answered" /> Terjawab</span><span><i className="legend-current" /> Sedang dibuka</span></div></div><div className="autosave"><ShieldCheck /> Simpan otomatis aktif</div></aside></div>{showExitDialog && <div className="dialog-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setShowExitDialog(false) }}><div className="confirm-dialog" role="alertdialog" aria-modal="true" aria-labelledby="exit-dialog-title" aria-describedby="exit-dialog-description" onKeyDown={(event) => { if (event.key === 'Escape') setShowExitDialog(false) }} onMouseDown={(event) => event.stopPropagation()}><h2 id="exit-dialog-title">Keluar dari asesmen?</h2><p id="exit-dialog-description">Anda akan kembali ke halaman pengantar asesmen.</p><div className="dialog-actions exit-dialog-actions"><button type="button" className="outline-button" autoFocus onClick={() => setShowExitDialog(false)}>Tetap mengerjakan</button><button type="button" className="danger-button" onClick={onBack}>Keluar</button></div></div></div>}</div>
}

function QuestionNavGroup({ label, numbers, current, isAnswered, onSelect }: { label: string; numbers: number[]; current: number; isAnswered: (index: number) => boolean; onSelect: (value: number) => void }) {
  return <div className="question-nav-group"><b>{label}</b><div>{numbers.map((number) => {
    const index = number - 1
    const answered = isAnswered(index)
    const status = current === index ? 'Sedang dibuka' : answered ? 'Terjawab' : 'Belum dijawab'
    return <button type="button" key={number} className={current === index ? 'active' : answered ? 'answered' : ''} aria-current={current === index ? 'step' : undefined} aria-label={`Pertanyaan ${number}, ${status}`} onClick={() => onSelect(index)}>{number}</button>
  })}</div></div>
}



export default function Page() { const router = useRouter(); const [active, setActive] = useState('Beranda'); const [sidebarCollapsed, setSidebarCollapsed] = useState(true); const [profile, setProfile] = useState({ email: 'vivi.zalzabilah@student.ac.id', name: 'Vivi Zalzabilah', nim: '23523230', faculty: 'Fakultas Teknik', major: 'Informatika' }); const render = active === 'Pengaturan Akun' ? <AccountSettingsView email={profile.email} /> : active === 'Profil Saya' ? <ProfileView profile={profile} onChange={setProfile} /> : active === 'Judul Tugas Akhir' ? <ThesisView /> : active === 'Mata Kuliah' ? <CourseRecommendation /> : active === 'Micro-Credential' ? <MicroView onReturnToHome={() => setActive('Beranda')} /> : <HomeView onSelect={setActive} />; return <div className={`app ${sidebarCollapsed ? 'app-sidebar-collapsed' : ''}`}><Sidebar active={active} onSelect={setActive} open={false} onClose={() => {}} collapsed={sidebarCollapsed} onToggle={() => setSidebarCollapsed((value) => !value)} onLogout={() => router.push('/login')} /><main className="main"><Topbar active={active} onSelect={setActive} /><AppContent>{render}</AppContent></main></div> }
