'use client'

import { useEffect, useState } from 'react'
import { ArrowLeft, BookOpen, CheckCircle2, Clock3, ListChecks, LogOut, PenLine, ShieldCheck, UserRound } from 'lucide-react'
import type { StudentProfile } from '@/components/shared/student-profile'
import { AssessmentProcessing } from './assessment-processing'
import { AssessmentResults } from './assessment-results'
import { emptyProfileQuestionAnswer, isProfileQuestionAnswered, ProfileQuestionFields, type ProfileQuestionAnswer } from './profile-question-fields'

type MicroTrack = 'Backend Engineer' | 'Data Analyst'
type AssessmentStage = 'tracks' | 'introduction' | 'theory' | 'processing' | 'results'
type TheoryQuestion = { question: string; options: string[]; topic?: string }

const microTracks: { title: MicroTrack; description: string; color: string; image: string }[] = [
  { title: 'Backend Engineer', description: 'Pelajari pengembangan API, desain basis data, microservices, dan teknologi backend modern.', color: 'blue', image: 'https://hebbkx1anhila5yf.public.blob.vercel-storage.com/backend_engineer-oXkb2OiGynHKE2yS547OIKldLrhbZO.png' },
  { title: 'Data Analyst', description: 'Pelajari analisis data, visualisasi, SQL, Python untuk data science, serta alat seperti Pandas dan Tableau.', color: 'mint', image: 'https://hebbkx1anhila5yf.public.blob.vercel-storage.com/data_analytics.jpg-QxcbQjAK3WzgfjuLbS1FQwsDONNqnW.webp' },
]

const essayQuestions: Record<MicroTrack, TheoryQuestion[]> = {
  'Backend Engineer': [
    { topic: 'http-methods', question: 'Jelaskan perbedaan PUT vs PATCH, lalu beri contoh request payload untuk update user.', options: [] },
    { topic: 'auth-implementation', question: 'Buat pseudo-code atau kode untuk endpoint POST /login yang memvalidasi input, verifikasi password hash, mengembalikan JWT ber-exp, dan mapping error 400/401/500 secara tepat.', options: [] },
    { topic: 'rate-limiting', question: 'Desain mekanisme rate limiting untuk public API multi-instance yang bisa handle burst, aman, efisien, dan mengembalikan response informatif saat limit tercapai.', options: [] },
  ],
  'Data Analyst': [
    { question: 'Jelaskan bagaimana Anda mengubah data mentah menjadi insight yang dapat ditindaklanjuti.', options: [] },
    { question: 'Jelaskan cara Anda memastikan kualitas data sebelum membuat laporan.', options: [] },
    { question: 'Jelaskan bagaimana Anda memilih visualisasi yang tepat untuk menyampaikan sebuah temuan.', options: [] },
  ],
}

const theoryQuestions: Record<MicroTrack, TheoryQuestion[]> = {
  'Backend Engineer': [
    { topic: 'http-authz', question: 'HTTP status code yang paling tepat untuk request valid tapi tidak memiliki akses ke resource adalah...', options: ['400 Bad Request', '401 Unauthorized', '403 Forbidden', '404 Not Found'] },
    { topic: 'database-indexing', question: 'Query: SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC LIMIT 20; Index yang paling efektif adalah...', options: ['index (created_at)', 'index (user_id)', 'composite index (user_id, created_at)', 'fulltext index pada orders'] },
    { topic: 'idempotency', question: 'Pada arsitektur microservices, untuk memastikan operasi create payment tidak dobel saat client retry (timeout), pendekatan paling tepat adalah...', options: ['Client dilarang retry', 'Tambahkan delay di client sebelum retry', 'Gunakan Idempotency-Key dan simpan hasil berdasarkan key', 'Gunakan GET instead of POST'] },
    { question: 'Manakah yang termasuk proses server-side?', options: ['Validasi dan pemrosesan data di server', 'Mengubah ukuran ikon di browser', 'Mengatur posisi tombol dengan CSS', 'Memilih tema perangkat pengguna'] },
    { question: 'Apa manfaat utama arsitektur microservices?', options: ['Semua fitur wajib berada dalam satu file', 'Layanan dapat dikembangkan dan diskalakan secara terpisah', 'Database tidak lagi diperlukan', 'Aplikasi hanya dapat berjalan offline'] },
  ],
  'Data Analyst': [
    { question: 'Apa tujuan utama eksplorasi data?', options: ['Memahami pola, kualitas, dan karakteristik data', 'Menghapus semua nilai yang berbeda', 'Mengganti database dengan spreadsheet', 'Membuat data tanpa sumber'] },
    { question: 'SQL digunakan terutama untuk...', options: ['Mengelola dan mengambil data dari database', 'Mendesain logo aplikasi', 'Mengompresi video', 'Mengatur koneksi Bluetooth'] },
    { question: 'Median adalah...', options: ['Nilai tengah setelah data diurutkan', 'Nilai terbesar dalam data', 'Jumlah seluruh data', 'Selisih nilai minimum dan maksimum'] },
    { question: 'Visualisasi yang tepat untuk melihat tren dari waktu ke waktu adalah...', options: ['Grafik garis', 'Diagram lingkaran tunggal', 'Tabel tanpa urutan', 'Ikon status'] },
    { question: 'Apa tujuan validasi data sebelum analisis?', options: ['Memastikan data akurat, konsisten, dan siap digunakan', 'Menambah duplikasi data', 'Menghilangkan semua outlier tanpa alasan', 'Membuat hasil tidak dapat direproduksi'] },
  ],
}

const profileQuestions = [
  'Masukkan jumlah seluruh proyek backend yang pernah Anda kerjakan, lalu pilih semua konteks proyek yang pernah Anda tangani.',
  'Teknologi/tools apa saja yang ingin Anda pelajari lebih mendalam? (Misalnya: Docker, AWS, GraphQL).',
  'Preferensi durasi kursus yang Anda inginkan?',
  'Apakah Anda tertarik dengan kursus berbayar atau gratis?',
]

export function MicroCredentialRecommendation({ onReturnToHome, studentProfile }: { onReturnToHome: () => void; studentProfile: StudentProfile }) {
  const [stage, setStage] = useState<AssessmentStage>('tracks')
  const [selectedTrack, setSelectedTrack] = useState<MicroTrack | null>(null)

  if (stage === 'introduction' && selectedTrack) return <AssessmentIntroduction track={selectedTrack} onBack={() => setStage('tracks')} onStart={() => setStage('theory')} />
  if (stage === 'theory' && selectedTrack) return <TheoryAssessment track={selectedTrack} onBack={() => setStage('introduction')} onSubmit={() => { document.querySelector<HTMLElement>('.main')?.scrollTo({ top: 0 }); setStage('processing') }} />
  if (stage === 'processing' && selectedTrack) return <AssessmentProcessing track={selectedTrack} onViewResult={() => { document.querySelector<HTMLElement>('.main')?.scrollTo({ top: 0 }); setStage('results') }} />
  if (stage === 'results' && selectedTrack) return <AssessmentResults track={selectedTrack} onReturnToHome={onReturnToHome} studentProfile={studentProfile} />

  return <div className="page-content micro-page"><div className="view-title micro-title"><div><h1>Temukan jalur belajar yang tepat</h1><p>Selesaikan asesmen, lalu AI akan merekomendasikan kursus yang sesuai dengan tingkat kemampuan Anda saat ini.</p></div><div className="hero-art mini"><span></span><span></span><span></span></div></div><div className="section-heading"><h2>Pilih track</h2></div><div className="track-grid">{microTracks.map((track) => <article className="track-card" key={track.title}><div className={`track-art ${track.color}`}><img src={track.image} alt="" /></div><div className="track-content"><h3>{track.title}</h3><p>{track.description}</p><div className="tags"><span>10 pertanyaan</span><span>15 menit</span></div><button type="button" className="primary full" onClick={() => { setSelectedTrack(track.title); setStage('introduction') }}>Mulai asesmen</button></div></article>)}</div></div>
}

function AssessmentIntroduction({ track, onBack, onStart }: { track: MicroTrack; onBack: () => void; onStart: () => void }) {
  const assessmentTypes = [
    { title: 'Tes Teori', description: 'Pertanyaan pilihan ganda untuk mengukur pemahaman Anda terhadap konsep-konsep dasar.', icon: ListChecks },
    { title: 'Esai', description: 'Pertanyaan tertulis untuk menilai kemampuan analisis dan cara Anda menjelaskan konsep.', icon: PenLine },
    { title: 'Profil', description: 'Tes singkat untuk mengetahui preferensi Anda dalam memilih micro-credential.', icon: UserRound },
  ]
  return <div className="page-content assessment-page"><button type="button" className="back-link" onClick={onBack}><ArrowLeft /> Kembali pilih track</button><div className="assessment-heading"><h1>Siap memulai asesmen?</h1></div><div className="selected-track-banner"><div><span>Track yang dipilih</span><strong>{track}</strong></div><span className="track-status"><CheckCircle2 /> Siap dimulai</span></div><div className="assessment-meta"><div><Clock3 /><span><b>15 menit</b><small>Estimasi waktu</small></span></div><div><ListChecks /><span><b>10 pertanyaan</b><small>Seluruh tes</small></span></div></div><div className="assessment-section-heading"><h2>Rangkaian asesmen</h2></div><div className="assessment-type-grid">{assessmentTypes.map(({ title, description, icon: Icon }, index) => <article className="assessment-type-card" key={title}><div className="assessment-type-number">{index + 1}</div><div className="assessment-type-icon"><Icon /></div><div><h3>{title}</h3><p>{description}</p></div></article>)}</div><button type="button" className="primary assessment-start" onClick={onStart}>Mulai Asesmen</button></div>
}

function TheoryAssessment({ track, onBack, onSubmit }: { track: MicroTrack; onBack: () => void; onSubmit: () => void }) {
  const questions = [...theoryQuestions[track], ...theoryQuestions[track]].slice(0, 10)
  const [current, setCurrent] = useState(0)
  const [answers, setAnswers] = useState<Record<number, number>>({})
  const [essayAnswers, setEssayAnswers] = useState<Record<number, string>>({})
  const [profileAnswers, setProfileAnswers] = useState<Record<number, ProfileQuestionAnswer>>({})
  const [secondsLeft, setSecondsLeft] = useState(14 * 60 + 52)
  const [showExitDialog, setShowExitDialog] = useState(false)
  const [showSubmitDialog, setShowSubmitDialog] = useState(false)
  const isEssay = current >= 3 && current <= 5
  const isProfile = current >= 6
  const question = isEssay ? essayQuestions[track][current - 3] : isProfile ? { question: profileQuestions[current - 6], options: [] } : questions[current]
  const essayAnswer = essayAnswers[current] ?? ''
  const profileAnswer = profileAnswers[current] ?? emptyProfileQuestionAnswer
  const isLast = current === questions.length - 1
  const minuteLabel = String(Math.floor(secondsLeft / 60)).padStart(2, '0')
  const secondLabel = String(secondsLeft % 60).padStart(2, '0')
  const questionNumbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
  const category = isEssay ? 'Esai' : isProfile ? 'Profil' : 'Teori'
  const topicTag = isEssay ? question.topic ?? 'http-methods' : isProfile ? null : question.topic ?? 'http-dutnz'
  const isAnswered = (index: number) => {
    if (index >= 3 && index <= 5) return Boolean(essayAnswers[index]?.trim())
    if (index >= 6 && index <= 9) return isProfileQuestionAnswered(index, profileAnswers[index] ?? emptyProfileQuestionAnswer)
    return answers[index] !== undefined
  }
  const updateProfileAnswer = (value: ProfileQuestionAnswer) => setProfileAnswers((previous) => ({ ...previous, [current]: value }))

  useEffect(() => {
    const timer = window.setInterval(() => setSecondsLeft((value) => Math.max(0, value - 1)), 1000)
    return () => window.clearInterval(timer)
  }, [])

  return <div className="page-content theory-screen"><div className="theory-screen-heading"><h1>{track}</h1><button type="button" className="exit-assessment exit-assessment-desktop" onClick={() => setShowExitDialog(true)}><LogOut /> Keluar</button><div className="mobile-assessment-toolbar"><div className="theory-toolbar-top"><div className="time-card time-card-compact"><span>Sisa waktu</span><strong><Clock3 /> {minuteLabel}:{secondLabel}</strong></div><button type="button" className="exit-assessment" onClick={() => setShowExitDialog(true)}><LogOut /> Keluar</button></div><div className="question-nav-card question-nav-card-inline"><h3>Navigasi pertanyaan</h3><div className="question-nav-groups"><QuestionNavGroup label="Teori" numbers={questionNumbers.slice(0, 3)} current={current} isAnswered={isAnswered} onSelect={setCurrent} /><QuestionNavGroup label="Esai" numbers={questionNumbers.slice(3, 6)} current={current} isAnswered={isAnswered} onSelect={setCurrent} /><QuestionNavGroup label="Profil" numbers={questionNumbers.slice(6)} current={current} isAnswered={isAnswered} onSelect={setCurrent} /></div><div className="question-legend"><span><i className="legend-empty" /> Belum dijawab</span><span><i className="legend-answered" /> Terjawab</span><span><i className="legend-current" /> Sedang dibuka</span></div></div></div></div><div className="theory-layout"><main className="theory-question-panel"><div className="theory-question-body"><div className="theory-question-top"><div><b>Pertanyaan {current + 1} dari 10</b><div className="theory-progress"><span style={{ width: `${((current + 1) / 10) * 100}%` }} /></div></div><strong>{Math.round(((current + 1) / 10) * 100)}%</strong></div><div className="theory-tags"><span>{isEssay ? <PenLine /> : isProfile ? <UserRound /> : <BookOpen />} {category}</span>{topicTag && <span>{topicTag}</span>}</div><h2>{question.question}</h2><div className="theory-hint"><span>i</span>{isEssay ? 'Jelaskan dengan kata-kata Anda sendiri. Susun jawaban secara runtut dan jelaskan alasan di balik setiap keputusan teknis.' : isProfile ? 'Lengkapi preferensi Anda agar rekomendasi kursus lebih sesuai.' : 'Pilih satu jawaban yang paling tepat.'}</div>{isEssay ? <div className="essay-answer"><label htmlFor="essay-response">Jawaban Anda</label><textarea id="essay-response" value={essayAnswer} onChange={(event) => setEssayAnswers((previous) => ({ ...previous, [current]: event.target.value }))} placeholder="Tulis jawaban Anda di sini..." /><div className="essay-meta"><span>{essayAnswer.trim() ? essayAnswer.trim().split(/\s+/).length : 0} kata</span><span><CheckCircle2 /> Jawaban tersimpan otomatis</span></div></div> : isProfile ? <ProfileQuestionFields questionNumber={current + 1} value={profileAnswer} onChange={updateProfileAnswer} /> : <div className="theory-options" role="radiogroup" aria-label={`Jawaban pertanyaan ${current + 1}`}>{question.options.map((option, index) => <button type="button" role="radio" aria-checked={answers[current] === index} className={`theory-option ${answers[current] === index ? 'selected' : ''}`} key={option} onClick={() => setAnswers((previous) => ({ ...previous, [current]: index }))}><span>{String.fromCharCode(65 + index)}</span><strong>{option}</strong>{answers[current] === index && <CheckCircle2 />}</button>)}</div>}</div><div className="theory-footer">{current > 0 && <button type="button" className="outline-button" onClick={() => setCurrent((value) => value - 1)}>Pertanyaan sebelumnya</button>}<button type="button" className="primary" onClick={() => isLast ? setShowSubmitDialog(true) : setCurrent((value) => value + 1)}>{isLast ? 'Kirim jawaban' : 'Pertanyaan berikutnya'}</button></div></main><aside className="theory-sidebar"><div className="time-card"><span>Sisa waktu</span><strong><Clock3 /> {minuteLabel}:{secondLabel}</strong></div><div className="question-nav-card"><h3>Navigasi pertanyaan</h3><QuestionNavGroup label="Teori" numbers={questionNumbers.slice(0, 3)} current={current} isAnswered={isAnswered} onSelect={setCurrent} /><QuestionNavGroup label="Esai" numbers={questionNumbers.slice(3, 6)} current={current} isAnswered={isAnswered} onSelect={setCurrent} /><QuestionNavGroup label="Profil" numbers={questionNumbers.slice(6)} current={current} isAnswered={isAnswered} onSelect={setCurrent} /><div className="question-legend"><span><i className="legend-empty" /> Belum dijawab</span><span><i className="legend-answered" /> Terjawab</span><span><i className="legend-current" /> Sedang dibuka</span></div></div><div className="autosave"><ShieldCheck /> Simpan otomatis aktif</div></aside></div>{showExitDialog && <div className="dialog-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setShowExitDialog(false) }}><div className="confirm-dialog" role="alertdialog" aria-modal="true" aria-labelledby="exit-dialog-title" aria-describedby="exit-dialog-description" onKeyDown={(event) => { if (event.key === 'Escape') setShowExitDialog(false) }} onMouseDown={(event) => event.stopPropagation()}><h2 id="exit-dialog-title">Keluar dari asesmen?</h2><p id="exit-dialog-description">Anda akan kembali ke halaman pengantar asesmen.</p><div className="dialog-actions exit-dialog-actions"><button type="button" className="outline-button" autoFocus onClick={() => setShowExitDialog(false)}>Tetap mengerjakan</button><button type="button" className="danger-button" onClick={onBack}>Keluar</button></div></div></div>}{showSubmitDialog && <div className="dialog-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setShowSubmitDialog(false) }}><div className="confirm-dialog" role="alertdialog" aria-modal="true" aria-labelledby="submit-dialog-title" aria-describedby="submit-dialog-description" onKeyDown={(event) => { if (event.key === 'Escape') setShowSubmitDialog(false) }} onMouseDown={(event) => event.stopPropagation()}><h2 id="submit-dialog-title">Kirim jawaban sekarang?</h2><p id="submit-dialog-description">Apakah Anda yakin ingin mengirim jawaban? Jawaban yang sudah dikirim tidak dapat diubah lagi.</p><div className="dialog-actions exit-dialog-actions"><button type="button" className="outline-button" autoFocus onClick={() => setShowSubmitDialog(false)}>Periksa lagi</button><button type="button" className="primary" onClick={() => { setShowSubmitDialog(false); onSubmit() }}>Ya, kirim</button></div></div></div>}</div>
}

function QuestionNavGroup({ label, numbers, current, isAnswered, onSelect }: { label: string; numbers: number[]; current: number; isAnswered: (index: number) => boolean; onSelect: (value: number) => void }) {
  return <div className="question-nav-group"><b>{label}</b><div>{numbers.map((number) => {
    const index = number - 1
    const answered = isAnswered(index)
    const status = current === index ? 'Sedang dibuka' : answered ? 'Terjawab' : 'Belum dijawab'
    return <button type="button" key={number} className={current === index ? 'active' : answered ? 'answered' : ''} aria-current={current === index ? 'step' : undefined} aria-label={`Pertanyaan ${number}, ${status}`} onClick={() => onSelect(index)}>{number}</button>
  })}</div></div>
}
