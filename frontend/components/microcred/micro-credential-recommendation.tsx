'use client'

import { useCallback, useEffect, useState } from 'react'
import { ArrowLeft, BookOpen, CheckCircle2, Clock3, ListChecks, Loader2, LogOut, PenLine, ShieldCheck, UserRound } from 'lucide-react'
import { AssessmentResults } from '@/components/assessment-results'
import { AssessmentProcessing } from '@/components/microcred/assessment-processing'
import {
  emptyProfileAnswerState,
  isProfileQuestionAnswered,
  normalizeOptions,
  ProfileQuestionFields,
  type ProfileAnswerState,
} from '@/components/microcred/profile-question-fields'
import { errorMessage } from '@/src/lib/api'
import {
  microcredService,
  type AnswerPayload,
  type AssessmentQuestion,
  type AssessmentResult,
  type AssessmentStart,
  type Track,
} from '@/src/services/microcred-service'

type AssessmentStage = 'tracks' | 'introduction' | 'theory' | 'processing' | 'results'

const trackColors = ['blue', 'lavender', 'mint', 'peach']
const trackImages = [
  'https://hebbkx1anhila5yf.public.blob.vercel-storage.com/backend_engineer-oXkb2OiGynHKE2yS547OIKldLrhbZO.png',
  'https://hebbkx1anhila5yf.public.blob.vercel-storage.com/cyber_security-FOXhXBLinDTZ4s6OoWVqogh84nmoOH.png',
  'https://hebbkx1anhila5yf.public.blob.vercel-storage.com/data_analytics.jpg-QxcbQjAK3WzgfjuLbS1FQwsDONNqnW.webp',
  'https://hebbkx1anhila5yf.public.blob.vercel-storage.com/frontend_engineer-Prf6N95a4lQjklHBto7UaWmxXqNTZu.png',
]

export function MicroCredentialRecommendation({
  studentName,
  onReturnToHome,
}: {
  studentName: string
  onReturnToHome: () => void
}) {
  const [stage, setStage] = useState<AssessmentStage>('tracks')
  const [tracks, setTracks] = useState<Track[]>([])
  const [loadingTracks, setLoadingTracks] = useState(true)
  const [selectedTrack, setSelectedTrack] = useState<Track | null>(null)
  const [assessment, setAssessment] = useState<AssessmentStart | null>(null)
  const [pendingResponses, setPendingResponses] = useState<AnswerPayload[]>([])
  const [starting, setStarting] = useState(false)
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

  function handleSubmit(responses: AnswerPayload[]) {
    setError('')
    setPendingResponses(responses)
    document.querySelector<HTMLElement>('.main')?.scrollTo({ top: 0 })
    setStage('processing')
  }

  const handleBackToQuestions = useCallback((message: string) => {
    setError(message)
    setStage('theory')
  }, [])

  const handleViewResult = useCallback((finalResult: AssessmentResult) => {
    setResult(finalResult)
    document.querySelector<HTMLElement>('.main')?.scrollTo({ top: 0 })
    setStage('results')
  }, [])

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

  if (stage === 'processing' && assessment && selectedTrack) {
    return (
      <AssessmentProcessing
        track={selectedTrack.name}
        assessmentId={assessment.assessment_id}
        responses={pendingResponses}
        onViewResult={handleViewResult}
        onBackToQuestions={handleBackToQuestions}
      />
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
      <div className="assessment-heading"><h1>Siap memulai asesmen?</h1></div>
      <div className="selected-track-banner">
        <div><span>Track yang dipilih</span><strong>{track.name}</strong></div>
        <span className="track-status"><CheckCircle2 /> Siap dimulai</span>
      </div>
      <div className="assessment-meta">
        <div><Clock3 /><span><b>15 menit</b><small>Estimasi waktu</small></span></div>
        <div><ListChecks /><span><b>{track.question_count} pertanyaan</b><small>Seluruh tes</small></span></div>
      </div>
      <div className="assessment-section-heading"><h2>Rangkaian asesmen</h2></div>
      <div className="assessment-type-grid">
        {assessmentTypes.map(({ title, description, icon: Icon }, index) => (
          <article className="assessment-type-card" key={title}>
            <div className="assessment-type-number">{index + 1}</div>
            <div className="assessment-type-icon"><Icon /></div>
            <div><h3>{title}</h3><p>{description}</p></div>
          </article>
        ))}
      </div>
      {error && <p className="form-error" role="alert">{error}</p>}
      <button type="button" className="primary assessment-start" onClick={onStart} disabled={starting}>
        {starting ? 'Menyiapkan soal...' : 'Mulai Asesmen'}
      </button>
    </div>
  )
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
  const [essayAnswers, setEssayAnswers] = useState<Record<string, string>>({})
  const [profileAnswers, setProfileAnswers] = useState<Record<string, ProfileAnswerState>>({})
  const [secondsLeft, setSecondsLeft] = useState(15 * 60)
  const [showExitDialog, setShowExitDialog] = useState(false)
  const [showSubmitDialog, setShowSubmitDialog] = useState(false)

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

  const isEssay = q.question_type === 'essay'
  const isProfile = q.question_type === 'profile'
  const opts = normalizeOptions(q.options)
  const category = isEssay ? 'Esai' : isProfile ? 'Profil' : 'Teori'

  const isAnswered = (index: number) => {
    const item = questions[index]
    if (!item) return false
    if (item.question_type === 'essay') return Boolean(essayAnswers[item.id]?.trim())
    if (item.question_type === 'profile') {
      return isProfileQuestionAnswered(item, profileAnswers[item.id] ?? emptyProfileAnswerState)
    }
    return Boolean(mcAnswers[item.id])
  }

  const theoryNumbers = questions.map((item, idx) => ({ item, num: idx + 1 })).filter((x) => x.item.question_type === 'theoretical').map((x) => x.num)
  const essayNumbers = questions.map((item, idx) => ({ item, num: idx + 1 })).filter((x) => x.item.question_type === 'essay').map((x) => x.num)
  const profileNumbers = questions.map((item, idx) => ({ item, num: idx + 1 })).filter((x) => x.item.question_type === 'profile').map((x) => x.num)

  function handleFinalSubmit() {
    const payload: AnswerPayload[] = questions.map((item) => {
      if (item.question_type === 'essay') {
        return { question_id: item.id, answer_text: (essayAnswers[item.id] ?? '').trim() }
      }
      if (item.question_type === 'theoretical') {
        const picked = mcAnswers[item.id]
        return { question_id: item.id, selected_option: picked, selected_option_id: picked }
      }
      const state = profileAnswers[item.id] ?? emptyProfileAnswerState
      const itemCaps = Array.isArray(item.metadata?.captures) ? (item.metadata?.captures as string[]) : []
      const itemOpts = normalizeOptions(item.options)
      const itemAcc = Array.isArray(item.metadata?.accepted_values) ? (item.metadata?.accepted_values as string[]) : []

      if (itemCaps.includes('project_count')) {
        return {
          question_id: item.id,
          project_count: Number(state.projectCount || 0),
          selected_options: state.selectedValues,
          project_contexts: state.selectedValues,
        }
      }
      if (itemOpts.length === 0 && itemAcc.length > 0) {
        const textItems = state.otherText.split(',').map((s) => s.trim()).filter(Boolean)
        const vals = [...new Map([...state.selectedValues, ...textItems].map((v) => [v.toLocaleLowerCase(), v])).values()]
        return { question_id: item.id, selected_options: vals, answer_text: vals.join(', ') }
      }
      if (itemOpts.length > 0) {
        return {
          question_id: item.id,
          selected_option: state.selectedOption || undefined,
          selected_option_id: state.selectedOption || undefined,
        }
      }
      return { question_id: item.id, answer_text: state.otherText.trim() }
    })
    setShowSubmitDialog(false)
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
                ? 'Jelaskan dengan kata-kata Anda sendiri. Susun jawaban secara runtut dan jelaskan alasan di balik setiap keputusan teknis.'
                : isProfile
                  ? 'Lengkapi preferensi Anda agar rekomendasi kursus lebih sesuai.'
                  : 'Pilih satu jawaban yang paling tepat.'}
            </div>

            {isEssay ? (
              <div className="essay-answer">
                <label htmlFor="essay-response">Jawaban Anda</label>
                <textarea
                  id="essay-response"
                  value={essayAnswers[q.id] ?? ''}
                  onChange={(event) => setEssayAnswers((previous) => ({ ...previous, [q.id]: event.target.value }))}
                  placeholder="Tulis jawaban Anda di sini..."
                />
                <div className="essay-meta">
                  <span>{(essayAnswers[q.id] ?? '').trim() ? (essayAnswers[q.id] ?? '').trim().split(/\s+/).length : 0} kata</span>
                  <span><CheckCircle2 /> Jawaban tersimpan di sesi ini</span>
                </div>
              </div>
            ) : isProfile ? (
              <ProfileQuestionFields
                question={q}
                value={profileAnswers[q.id] ?? emptyProfileAnswerState}
                onChange={(nextVal) => setProfileAnswers((prev) => ({ ...prev, [q.id]: nextVal }))}
              />
            ) : (
              <div className="theory-options" role="radiogroup" aria-label={`Jawaban pertanyaan ${current + 1}`}>
                {opts.map((option) => (
                  <button
                    type="button"
                    role="radio"
                    aria-checked={mcAnswers[q.id] === option.id}
                    className={`theory-option ${mcAnswers[q.id] === option.id ? 'selected' : ''}`}
                    key={option.id}
                    onClick={() => setMcAnswers((previous) => ({ ...previous, [q.id]: option.id }))}
                  >
                    <span>{option.id}</span>
                    <strong>{option.text}</strong>
                    {mcAnswers[q.id] === option.id && <CheckCircle2 />}
                  </button>
                ))}
              </div>
            )}
            {error && <p className="form-error" role="alert" style={{ marginTop: '12px' }}>{error}</p>}
          </div>

          <div className="theory-footer">
            {current > 0 && (
              <button type="button" className="outline-button" onClick={() => setCurrent((value) => value - 1)}>
                Pertanyaan sebelumnya
              </button>
            )}
            <button type="button" className="primary" onClick={() => isLast ? setShowSubmitDialog(true) : setCurrent((value) => value + 1)}>
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

      {showSubmitDialog && (
        <div className="dialog-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setShowSubmitDialog(false) }}>
          <div className="confirm-dialog" role="alertdialog" aria-modal="true" aria-labelledby="submit-dialog-title" aria-describedby="submit-dialog-description" onKeyDown={(event) => { if (event.key === 'Escape') setShowSubmitDialog(false) }} onMouseDown={(event) => event.stopPropagation()}>
            <h2 id="submit-dialog-title">Kirim jawaban sekarang?</h2>
            <p id="submit-dialog-description">Apakah Anda yakin ingin mengirim jawaban? Jawaban yang sudah dikirim tidak dapat diubah lagi.</p>
            <div className="dialog-actions exit-dialog-actions">
              <button type="button" className="outline-button" autoFocus onClick={() => setShowSubmitDialog(false)}>Periksa lagi</button>
              <button type="button" className="primary" onClick={handleFinalSubmit}>Ya, kirim</button>
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
