'use client'

import { Fragment, useState, type KeyboardEvent, type ReactNode } from 'react'
import { BarChart3, CheckCircle2, Clock3, Home, Info, Mail, Star, Users } from 'lucide-react'
import { AssessmentScoreSummary } from '@/components/microcred/assessment-score-summary'
import { CourseFeedback } from '@/components/microcred/course-feedback'
import { errorMessage } from '@/src/lib/api'
import { microcredService, type AssessmentResult, type RecommendedCourse } from '@/src/services/microcred-service'

function num(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

function pickString(meta: Record<string, unknown> | null | undefined, keys: string[]): string | null {
  if (!meta) return null
  for (const key of keys) {
    const val = meta[key]
    if (typeof val === 'string' && val.trim()) return val.trim()
  }
  return null
}

function renderInlineMarkdown(text: string): ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g)
  return parts.map((part, idx) => {
    if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
      return <strong key={idx}>{part.slice(2, -2)}</strong>
    }
    if (part.startsWith('*') && part.endsWith('*') && part.length > 2) {
      return <em key={idx}>{part.slice(1, -1)}</em>
    }
    if (part.startsWith('`') && part.endsWith('`') && part.length > 2) {
      return <code key={idx}>{part.slice(1, -1)}</code>
    }
    return <Fragment key={idx}>{part}</Fragment>
  })
}

function FormattedSummary({ content }: { content: string }) {
  const lines = content.replace(/\r\n/g, '\n').split('\n')
  const blocks: ReactNode[] = []
  let i = 0

  while (i < lines.length) {
    const trimmed = lines[i].trim()
    if (!trimmed) { i += 1; continue }

    if (/^(-{3,}|\*{3,}|_{3,})$/.test(trimmed)) {
      blocks.push(<hr key={`hr-${i}`} />)
      i += 1
      continue
    }

    const headingMatch = trimmed.match(/^(#{1,4})\s+(.+)$/)
    if (headingMatch) {
      const level = headingMatch[1].length
      const headingText = renderInlineMarkdown(headingMatch[2])
      blocks.push(
        level <= 2
          ? <h4 key={`h-${i}`} className="summary-heading-lg">{headingText}</h4>
          : <h5 key={`h-${i}`} className="summary-heading-sm">{headingText}</h5>,
      )
      i += 1
      continue
    }

    if (/^[-*+]\s+/.test(trimmed)) {
      const items: string[] = []
      while (i < lines.length && /^[-*+]\s+/.test(lines[i].trim())) {
        items.push(lines[i].trim().replace(/^[-*+]\s+/, ''))
        i += 1
      }
      blocks.push(
        <ul key={`ul-${i}`} className="summary-list">
          {items.map((item, idx) => <li key={idx}>{renderInlineMarkdown(item)}</li>)}
        </ul>,
      )
      continue
    }

    if (/^\d+\.\s+/.test(trimmed)) {
      const items: string[] = []
      while (i < lines.length && /^\d+\.\s+/.test(lines[i].trim())) {
        items.push(lines[i].trim().replace(/^\d+\.\s+/, ''))
        i += 1
      }
      blocks.push(
        <ol key={`ol-${i}`} className="summary-list">
          {items.map((item, idx) => <li key={idx}>{renderInlineMarkdown(item)}</li>)}
        </ol>,
      )
      continue
    }

    const paragraphLines: string[] = []
    while (
      i < lines.length &&
      lines[i].trim() !== '' &&
      !/^#{1,4}\s+/.test(lines[i].trim()) &&
      !/^[-*+]\s+/.test(lines[i].trim()) &&
      !/^\d+\.\s+/.test(lines[i].trim()) &&
      !/^(-{3,}|\*{3,}|_{3,})$/.test(lines[i].trim())
    ) {
      paragraphLines.push(lines[i].trim())
      i += 1
    }
    blocks.push(<p key={`p-${i}`}>{renderInlineMarkdown(paragraphLines.join(' '))}</p>)
  }

  return <div className="assessment-summary-rich">{blocks}</div>
}

function CourseCard({ course }: { course: RecommendedCourse }) {
  const meta = course.metadata ?? null
  const level = pickString(meta, ['level', 'difficulty'])
  const duration = pickString(meta, ['duration', 'duration_hours'])
  const students = pickString(meta, ['students', 'num_subscribers'])
  const rating = num(meta?.rating)
  const focus = pickString(meta, ['focus', 'skill', 'topic'])
  const courseUrl = course.course_url || `https://www.udemy.com/courses/search/?q=${encodeURIComponent(course.course_title)}`
  const matchPct = course.relevance_score <= 1 ? Math.round(course.relevance_score * 100) : Math.round(course.relevance_score)

  return (
    <article className="assessment-course-card">
      <div className="assessment-course-topline">
        <span>Peringkat {course.rank}</span>
        <strong>{matchPct}% cocok</strong>
      </div>
      <h4>{course.course_title}</h4>
      {focus && (
        <div className="assessment-course-tags">
          <span>Sesuai minat: {focus}</span>
        </div>
      )}
      {course.match_reason && <p style={{ fontSize: '12px', color: '#43567d', lineHeight: 1.55, margin: '0 0 12px' }}>{course.match_reason}</p>}
      {(level || duration || students || rating !== null) && (
        <dl className="assessment-course-meta">
          {level && <div><dt className="sr-only">Level</dt><dd><BarChart3 aria-hidden="true" /> {level}</dd></div>}
          {duration && <div><dt className="sr-only">Durasi</dt><dd><Clock3 aria-hidden="true" /> {duration}</dd></div>}
          {students && <div><dt className="sr-only">Total siswa</dt><dd><Users aria-hidden="true" /> {students}</dd></div>}
          {rating !== null && <div><dt className="sr-only">Rating</dt><dd className="assessment-course-rating"><Star aria-hidden="true" /> {rating.toFixed(1)}</dd></div>}
        </dl>
      )}
      <a className="assessment-course-link" href={courseUrl} target="_blank" rel="noreferrer">Lihat kursus</a>
    </article>
  )
}

export function AssessmentResults({
  result,
  trackName,
  studentName,
  onReturnToHome,
}: {
  result: AssessmentResult
  trackName: string
  studentName: string
  onReturnToHome: () => void
}) {
  const [activeCourseTab, setActiveCourseTab] = useState<'foundation' | 'target'>('foundation')
  const [emailStatus, setEmailStatus] = useState<string | null>(null)
  const [sendingEmail, setSendingEmail] = useState(false)

  const breakdown = result.score_breakdown ?? {}
  const theoScore = num(breakdown.theoretical?.score ?? breakdown.theoretical?.total) ?? 0
  const essayScore = num(breakdown.essay?.score ?? breakdown.essay?.total) ?? 0
  const profileScore = num(breakdown.profile?.score ?? breakdown.profile?.total) ?? 0
  const overallScore = num(result.overall_score ?? breakdown.overall?.score ?? breakdown.overall?.total) ?? (theoScore + essayScore + profileScore)
  const maxScore = num(breakdown.overall?.max) ?? 1000

  const recommendations = result.recommendations ?? []
  const foundation = recommendations.slice(0, 5)
  const target = recommendations.slice(5)

  const handleCourseTabKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return
    event.preventDefault()
    const next = activeCourseTab === 'foundation' ? 'target' : 'foundation'
    setActiveCourseTab(next)
    document.getElementById(`course-tab-${next}`)?.focus()
  }

  async function handleSendEmail() {
    if (sendingEmail) return
    setSendingEmail(true)
    setEmailStatus(null)
    try {
      const res = await microcredService.emailSummary(result.assessment_id)
      setEmailStatus(`Ringkasan hasil asesmen telah dikirim ke ${res.to_email}.`)
    } catch (caught) {
      setEmailStatus(errorMessage(caught, 'Gagal mengirim email ringkasan.'))
    } finally {
      setSendingEmail(false)
    }
  }

  return (
    <div className="page-content assessment-results">
      <section className="assessment-result-hero" aria-labelledby="assessment-result-title">
        <span className="assessment-result-status"><CheckCircle2 /> Asesmen selesai</span>
        <h1 id="assessment-result-title">Hasil asesmen {trackName}</h1>
        <p className="assessment-result-greeting">Halo, <strong>{studentName}</strong></p>
        <p className="assessment-result-intro">Berikut ringkasan skor, analisis AI, dan rekomendasi kursus yang sesuai untuk Anda.</p>
        {result.degraded && (
          <p className="account-settings-result-note" style={{ marginTop: '12px' }}>
            Sebagian analisis berjalan dalam mode cadangan karena layanan penilaian AI sedang terbatas.
          </p>
        )}
        <div className="assessment-result-actions">
          <button type="button" className="outline-button" onClick={onReturnToHome}><Home /> Kembali ke beranda</button>
          <button type="button" className="primary" onClick={handleSendEmail} disabled={sendingEmail}>
            <Mail /> {sendingEmail ? 'Mengirim...' : 'Kirim ke email'}
          </button>
        </div>
        {emailStatus && <p className="account-settings-feedback" role="status" style={{ marginTop: '12px' }}>{emailStatus}</p>}
      </section>

      <section className="assessment-result-section" aria-labelledby="score-summary-title">
        <h2 id="score-summary-title">Ringkasan skor</h2>
        <AssessmentScoreSummary
          theoryScore={theoScore}
          essayScore={essayScore}
          profileScore={profileScore}
          overallScore={overallScore}
          maxScore={maxScore}
        />
      </section>

      {result.summary && (
        <section className="assessment-result-section" aria-labelledby="analysis-title">
          <h2 id="analysis-title">Analisis AI</h2>
          <div className="assessment-analysis-grid">
            <article className="assessment-analysis-card" style={{ gridColumn: '1 / -1' }}>
              <div className="assessment-analysis-title">
                <h3>Ringkasan Kompetensi</h3>
                <strong>{overallScore.toLocaleString('id-ID', { minimumFractionDigits: 1, maximumFractionDigits: 1 })} poin</strong>
              </div>
              <FormattedSummary content={result.summary} />
            </article>
          </div>
        </section>
      )}

      <section className="assessment-result-section" aria-labelledby="course-recommendations-title">
        <h2 id="course-recommendations-title">Rekomendasi kursus</h2>
        <div className="assessment-recommendation-note">
          <Info />
          <div>
            <p>Jalur target bersifat aspirasional. Selesaikan Fondasi Wajib terlebih dahulu untuk mengurangi risiko kesulitan belajar sebelum melanjutkan ke jalur target pada track {trackName}.</p>
          </div>
        </div>
        {recommendations.length === 0 ? (
          <div className="activity-result-empty" style={{ marginTop: '16px' }}>Belum ada rekomendasi kursus yang dihasilkan.</div>
        ) : (
          <>
            <div className="assessment-course-tabs" role="tablist" aria-label="Kategori rekomendasi kursus">
              <button
                type="button"
                role="tab"
                id="course-tab-foundation"
                aria-controls="course-panel-foundation"
                aria-selected={activeCourseTab === 'foundation'}
                tabIndex={activeCourseTab === 'foundation' ? 0 : -1}
                className={activeCourseTab === 'foundation' ? 'active' : ''}
                onClick={() => setActiveCourseTab('foundation')}
                onKeyDown={handleCourseTabKeyDown}
              >
                Tahap 1: Fondasi Wajib ({foundation.length})
              </button>
              <button
                type="button"
                role="tab"
                id="course-tab-target"
                aria-controls="course-panel-target"
                aria-selected={activeCourseTab === 'target'}
                tabIndex={activeCourseTab === 'target' ? 0 : -1}
                className={activeCourseTab === 'target' ? 'active' : ''}
                onClick={() => setActiveCourseTab('target')}
                onKeyDown={handleCourseTabKeyDown}
              >
                Tahap 2: Jalur Target ({target.length})
              </button>
            </div>
            {activeCourseTab === 'foundation' ? (
              <div role="tabpanel" id="course-panel-foundation" aria-labelledby="course-tab-foundation">
                <div className="assessment-course-heading">
                  <div><h3>Fondasi Wajib</h3><p>Selesaikan jalur ini terlebih dahulu untuk meningkatkan peluang berhasil pada topik target.</p></div>
                </div>
                <div className="assessment-course-grid">
                  {foundation.map((course) => <CourseCard course={course} key={`${course.rank}-${course.course_id}`} />)}
                </div>
              </div>
            ) : (
              <div role="tabpanel" id="course-panel-target" aria-labelledby="course-tab-target">
                <div className="assessment-course-heading">
                  <div><h3>Jalur Target (Aspirasional)</h3><p>Jalur minat Anda, direkomendasikan setelah fondasi selesai.</p></div>
                </div>
                {target.length === 0 ? (
                  <div className="activity-result-empty">Tidak ada kursus tambahan pada tahap lanjutan.</div>
                ) : (
                  <div className="assessment-course-grid target">
                    {target.map((course) => <CourseCard course={course} key={`${course.rank}-${course.course_id}`} />)}
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </section>

      <CourseFeedback assessmentId={result.assessment_id} courses={recommendations} />
    </div>
  )
}
