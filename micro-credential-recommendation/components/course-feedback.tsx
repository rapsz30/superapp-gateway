import { useId, useState, type FormEvent } from 'react'
import { AlertCircle, CheckCircle2, Loader2 } from 'lucide-react'

const feedbackCourses = [
  'Beginner to Pro in Excel: Financial Modeling and Valuation',
  'Learn E-Commerce Website in PHP & MySQL From Scratch!',
  'Excel Crash Course: Master Excel for Financial Analysis',
  'Projects in PHP and MySQL',
  'Professional Python Web Development Using Flask',
]

const relevanceOptions = [
  { value: '0', label: '0 - Tidak Relevan' },
  { value: '1', label: '1 - Cukup Relevan' },
  { value: '2', label: '2 - Sangat Relevan' },
]

const scaleOptions = [1, 2, 3, 4, 5]

type Status = 'idle' | 'submitting' | 'success' | 'error'

async function submitCourseFeedback(payload: unknown) {
  await new Promise((resolve) => setTimeout(resolve, 900))
  return payload
}

function RatingScale({ name, label, hint, value, onChange, invalid }: { name: string; label: string; hint: string; value: number | null; onChange: (value: number) => void; invalid: boolean }) {
  const hintId = useId()
  return <fieldset className={`course-feedback-scale${invalid ? ' invalid' : ''}`} aria-describedby={hintId}>
    <legend>{label}</legend>
    <p id={hintId}>{hint}</p>
    <div className="course-feedback-scale-options">
      {scaleOptions.map((option) => <label key={option} className={value === option ? 'selected' : ''}>
        <input type="radio" name={name} value={option} checked={value === option} onChange={() => onChange(option)} />
        <span>{option}</span>
      </label>)}
    </div>
    {invalid && <span className="course-feedback-error" role="alert">Pilih nilai 1–5.</span>}
  </fieldset>
}

export function CourseFeedback() {
  const [courseRatings, setCourseRatings] = useState<string[]>(() => feedbackCourses.map(() => ''))
  const [relevance, setRelevance] = useState<number | null>(null)
  const [acceptance, setAcceptance] = useState<number | null>(null)
  const [comment, setComment] = useState('')
  const [showErrors, setShowErrors] = useState(false)
  const [status, setStatus] = useState<Status>('idle')

  const missingCourse = courseRatings.some((rating) => rating === '')
  const isValid = !missingCourse && relevance !== null && acceptance !== null
  const isLocked = status === 'submitting' || status === 'success'

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (status === 'submitting') return
    if (!isValid) {
      setShowErrors(true)
      return
    }
    setStatus('submitting')
    try {
      await submitCourseFeedback({
        courses: feedbackCourses.map((title, index) => ({ rank: index + 1, title, relevance: Number(courseRatings[index]) })),
        relevance,
        acceptance,
        comment: comment.trim(),
      })
      setStatus('success')
    } catch {
      setStatus('error')
    }
  }

  return <section className="assessment-result-section course-feedback" aria-labelledby="course-feedback-title">
    <h2 id="course-feedback-title">Berikan Feedback</h2>
    <p className="course-feedback-intro">Bantu kami meningkatkan kualitas rekomendasi kursus dengan memberikan penilaian singkat.</p>

    <form className="course-feedback-card" onSubmit={handleSubmit} noValidate>
      <fieldset className="course-feedback-group" disabled={isLocked}>
        <legend>Relevansi Setiap Kursus (Top 5)</legend>
        <p>Berikan penilaian terhadap relevansi setiap kursus berikut dengan kebutuhan belajar Anda.</p>
        <ol className="course-feedback-list">
          {feedbackCourses.map((title, index) => {
            const selectId = `course-feedback-${index}`
            const invalid = showErrors && courseRatings[index] === ''
            return <li key={title} className={invalid ? 'invalid' : ''}>
              <span className="course-feedback-rank" aria-hidden="true">#{index + 1}</span>
              <label htmlFor={selectId}><span className="sr-only">{`Peringkat ${index + 1}: `}</span>{title}</label>
              <select id={selectId} value={courseRatings[index]} aria-invalid={invalid} onChange={(event) => setCourseRatings((current) => current.map((rating, i) => (i === index ? event.target.value : rating)))}>
                <option value="" disabled>Pilih relevansi</option>
                {relevanceOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
              </select>
            </li>
          })}
        </ol>
        {showErrors && missingCourse && <span className="course-feedback-error" role="alert">Beri penilaian untuk semua kursus.</span>}
      </fieldset>

      <fieldset className="course-feedback-overall" disabled={isLocked}>
        <legend className="sr-only">Penilaian Keseluruhan</legend>
        <RatingScale name="feedback-relevance" label="Relevansi (1–5)" hint="Seberapa relevan rekomendasi secara keseluruhan dengan kebutuhan belajar Anda?" value={relevance} onChange={setRelevance} invalid={showErrors && relevance === null} />
        <RatingScale name="feedback-acceptance" label="Penerimaan (1–5)" hint="Seberapa besar kemungkinan Anda mengikuti kursus yang direkomendasikan?" value={acceptance} onChange={setAcceptance} invalid={showErrors && acceptance === null} />
      </fieldset>

      <div className="course-feedback-comment">
        <label htmlFor="course-feedback-comment">Komentar</label>
        <textarea id="course-feedback-comment" rows={4} maxLength={1000} value={comment} disabled={isLocked} onChange={(event) => setComment(event.target.value)} placeholder="Apa yang paling membantu atau kurang relevan dari rekomendasi ini?" />
      </div>

      <div className="course-feedback-footer">
        <div aria-live="polite">
          {status === 'success' && <p className="course-feedback-message success"><CheckCircle2 aria-hidden="true" /> Terima kasih, feedback Anda berhasil dikirim.</p>}
          {status === 'error' && <p className="course-feedback-message error" role="alert"><AlertCircle aria-hidden="true" /> Gagal mengirim feedback. Silakan coba lagi.</p>}
        </div>
        <button type="submit" className="primary" disabled={isLocked} aria-busy={status === 'submitting'}>
          {status === 'submitting' ? <><Loader2 className="course-feedback-spinner" aria-hidden="true" /> Mengirim...</> : status === 'success' ? 'Feedback terkirim' : 'Kirim Feedback'}
        </button>
      </div>
    </form>
  </section>
}
