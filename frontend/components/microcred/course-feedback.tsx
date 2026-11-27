'use client'

import { useId, useState, type FormEvent } from 'react'
import { AlertCircle, CheckCircle2, Loader2 } from 'lucide-react'
import { errorMessage } from '@/src/lib/api'
import { microcredService, type RecommendedCourse } from '@/src/services/microcred-service'

const relevanceOptions = [
  { value: '0', label: '0 - Tidak Relevan' },
  { value: '1', label: '1 - Cukup Relevan' },
  { value: '2', label: '2 - Sangat Relevan' },
]

const scaleOptions = [1, 2, 3, 4, 5]

type Status = 'idle' | 'submitting' | 'success' | 'error'

function RatingScale({
  name,
  label,
  hint,
  value,
  onChange,
  invalid,
}: {
  name: string
  label: string
  hint: string
  value: number | null
  onChange: (value: number) => void
  invalid: boolean
}) {
  const hintId = useId()
  return (
    <fieldset className={`course-feedback-scale${invalid ? ' invalid' : ''}`} aria-describedby={hintId}>
      <legend>{label}</legend>
      <p id={hintId}>{hint}</p>
      <div className="course-feedback-scale-options">
        {scaleOptions.map((option) => (
          <label key={option} className={value === option ? 'selected' : ''}>
            <input type="radio" name={name} value={option} checked={value === option} onChange={() => onChange(option)} />
            <span>{option}</span>
          </label>
        ))}
      </div>
      {invalid && <span className="course-feedback-error" role="alert">Pilih nilai 1–5.</span>}
    </fieldset>
  )
}

export function CourseFeedback({ assessmentId, courses }: { assessmentId: string; courses: RecommendedCourse[] }) {
  const feedbackCourses = courses.slice(0, 5)
  const [courseRatings, setCourseRatings] = useState<string[]>(() => feedbackCourses.map(() => ''))
  const [relevance, setRelevance] = useState<number | null>(null)
  const [acceptance, setAcceptance] = useState<number | null>(null)
  const [comment, setComment] = useState('')
  const [showErrors, setShowErrors] = useState(false)
  const [status, setStatus] = useState<Status>('idle')
  const [errorMsg, setErrorMsg] = useState('')

  const missingCourse = feedbackCourses.length > 0 && courseRatings.some((rating) => rating === '')
  const isValid = !missingCourse && relevance !== null && acceptance !== null
  const isLocked = status === 'submitting' || status === 'success'

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (status === 'submitting') return
    if (!isValid || relevance === null || acceptance === null) {
      setShowErrors(true)
      return
    }
    setStatus('submitting')
    setErrorMsg('')
    try {
      await microcredService.submitFeedback(assessmentId, {
        rating_relevance: relevance,
        rating_acceptance: acceptance,
        item_ratings: feedbackCourses.length
          ? feedbackCourses.map((course, index) => ({
              rank: course.rank || index + 1,
              course_id: course.course_id,
              relevance_score_0_2: Number(courseRatings[index]),
            }))
          : undefined,
        comment: comment.trim() || undefined,
      })
      setStatus('success')
    } catch (caught) {
      setErrorMsg(errorMessage(caught, 'Gagal mengirim feedback. Silakan coba lagi.'))
      setStatus('error')
    }
  }

  return (
    <section className="assessment-result-section course-feedback" aria-labelledby="course-feedback-title">
      <h2 id="course-feedback-title">Berikan Feedback</h2>
      <p className="course-feedback-intro">Bantu kami meningkatkan kualitas rekomendasi kursus dengan memberikan penilaian singkat.</p>

      <form className="course-feedback-card" onSubmit={handleSubmit} noValidate>
        {feedbackCourses.length > 0 && (
          <fieldset className="course-feedback-group" disabled={isLocked}>
            <legend>Relevansi Setiap Kursus (Top {feedbackCourses.length})</legend>
            <p>Berikan penilaian terhadap relevansi setiap kursus berikut dengan kebutuhan belajar Anda.</p>
            <ol className="course-feedback-list">
              {feedbackCourses.map((course, index) => {
                const selectId = `course-feedback-${index}`
                const invalid = showErrors && courseRatings[index] === ''
                return (
                  <li key={`${course.rank}-${course.course_id}`} className={invalid ? 'invalid' : ''}>
                    <span className="course-feedback-rank" aria-hidden="true">#{index + 1}</span>
                    <label htmlFor={selectId}>
                      <span className="sr-only">{`Peringkat ${index + 1}: `}</span>
                      {course.course_title}
                    </label>
                    <select
                      id={selectId}
                      value={courseRatings[index]}
                      aria-invalid={invalid}
                      onChange={(event) => setCourseRatings((current) => current.map((rating, i) => (i === index ? event.target.value : rating)))}
                    >
                      <option value="" disabled>Pilih relevansi</option>
                      {relevanceOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
                    </select>
                  </li>
                )
              })}
            </ol>
            {showErrors && missingCourse && <span className="course-feedback-error" role="alert">Beri penilaian untuk semua kursus.</span>}
          </fieldset>
        )}

        <fieldset className="course-feedback-overall" disabled={isLocked}>
          <legend className="sr-only">Penilaian Keseluruhan</legend>
          <RatingScale
            name="feedback-relevance"
            label="Relevansi (1–5)"
            hint="Seberapa relevan rekomendasi secara keseluruhan dengan kebutuhan belajar Anda?"
            value={relevance}
            onChange={setRelevance}
            invalid={showErrors && relevance === null}
          />
          <RatingScale
            name="feedback-acceptance"
            label="Penerimaan (1–5)"
            hint="Seberapa besar kemungkinan Anda mengikuti kursus yang direkomendasikan?"
            value={acceptance}
            onChange={setAcceptance}
            invalid={showErrors && acceptance === null}
          />
        </fieldset>

        <div className="course-feedback-comment">
          <label htmlFor="course-feedback-comment">Komentar</label>
          <textarea
            id="course-feedback-comment"
            rows={4}
            maxLength={1000}
            value={comment}
            disabled={isLocked}
            onChange={(event) => setComment(event.target.value)}
            placeholder="Apa yang paling membantu atau kurang relevan dari rekomendasi ini?"
          />
        </div>

        <div className="course-feedback-footer">
          <div aria-live="polite">
            {status === 'success' && <p className="course-feedback-message success"><CheckCircle2 aria-hidden="true" /> Terima kasih, feedback Anda berhasil dikirim.</p>}
            {status === 'error' && <p className="course-feedback-message error" role="alert"><AlertCircle aria-hidden="true" /> {errorMsg}</p>}
          </div>
          <button type="submit" className="primary" disabled={isLocked} aria-busy={status === 'submitting'}>
            {status === 'submitting' ? (
              <><Loader2 className="course-feedback-spinner" aria-hidden="true" /> Mengirim...</>
            ) : status === 'success' ? (
              'Feedback terkirim'
            ) : (
              'Kirim Feedback'
            )}
          </button>
        </div>
      </form>
    </section>
  )
}
