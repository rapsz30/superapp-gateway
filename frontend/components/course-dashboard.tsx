'use client'

import { useCallback, useEffect, useState } from 'react'
import { AlertTriangle, ArrowRight, Loader2 } from 'lucide-react'
import { SubmissionBadge } from '@/components/submission-badge'
import { SubmitCard } from '@/components/submit-card'
import { errorMessage } from '@/src/lib/api'
import { khsService } from '@/src/services/khs-services'
import { pengajuanService, type AcademicSummary, type CourseGrade, type Submission } from '@/src/services/pengajuan-service'
import type { GuideInfo } from '@/src/types/khs'

const gradeStatus: Record<CourseGrade['status'], string> = { lulus: 'Lulus', bersyarat: 'Disarankan diulang', tidak_lulus: 'Wajib diulang' }
const formatDate = (value: string) => new Date(value).toLocaleDateString('id-ID', { day: 'numeric', month: 'long', year: 'numeric' })
const formatGpa = (value: number | null) => value === null ? '—' : value.toFixed(2)
const semesterLabel = (semester: number) => semester === 0 ? 'Semester tidak terbaca' : `Semester ${semester}`

type Props = {
  studentId: string
  name?: string
  submission: Submission | null
  loading: boolean
  error: string
  onRetry: () => void
  onChange: (value: Submission) => void
  /** Pengisian form sudah dimulai dan belum diulang dari awal. */
  started: boolean
  onStart: () => void
}

/** Halaman awal Mata Kuliah: status pengajuan, ringkasan nilai dari KHS terakhir, rencana studi, dan riwayat. */
export function CourseDashboard({ studentId, name, submission, loading, error, onRetry, onChange, started, onStart }: Props) {
  const [guide, setGuide] = useState<GuideInfo | null>(null)
  const [guideError, setGuideError] = useState('')
  const [history, setHistory] = useState<Submission[]>([])
  const [historyError, setHistoryError] = useState('')
  const [chosen, setChosen] = useState<Submission | null>(null)
  const [approved, setApproved] = useState<Submission | null>(null)

  useEffect(() => {
    let active = true
    khsService.getGuide()
      .then((value) => { if (active) setGuide(value) })
      .catch((caught) => { if (active) setGuideError(errorMessage(caught, 'Panduan akademik tidak dapat dimuat.')) })
    return () => { active = false }
  }, [])

  const loadHistory = useCallback(() => {
    setHistoryError('')
    pengajuanService.history(studentId).then(setHistory).catch((caught) => setHistoryError(errorMessage(caught, 'Riwayat tidak dapat dimuat.')))
  }, [studentId])
  useEffect(loadHistory, [loadHistory, submission?.id, submission?.status])

  const current = submission && submission.status !== 'dibatalkan' ? submission : null
  const open = current?.status === 'diajukan'

  // Bila pengajuan terakhir tidak punya rencana (batal atau masih diproses), tampilkan rencana disetujui yang terakhir.
  const currentHasPlan = !!current?.rencana?.rencana_mk?.length
  const approvedId = history.find((item) => item.status === 'disetujui')?.id
  useEffect(() => {
    if (currentHasPlan || !approvedId) { setApproved(null); return }
    let active = true
    pengajuanService.get(approvedId).then((value) => { if (active) setApproved(value) }).catch(() => undefined)
    return () => { active = false }
  }, [currentHasPlan, approvedId])

  const shownPlan = chosen ?? (currentHasPlan ? current : approved)

  function choose(id: string) {
    setHistoryError('')
    pengajuanService.get(id).then(setChosen).catch((caught) => setHistoryError(errorMessage(caught, 'Rencana tidak dapat dimuat.')))
  }

  const startLabel = started ? 'Lanjutkan pengisian' : current ? 'Ajukan rencana baru' : 'Ajukan rencana studi'

  return <div className="page-content course-page course-dashboard">
    <div className="course-heading">
      <div>
        <h1>{name ? `Halo, ${name}` : 'Perencanaan studi'}</h1>
        <p>{guide ? `Program studi ${guide.program}${guide.advisorName ? ` · Pembimbing akademik: ${guide.advisorName}` : ' · Pembimbing akademik belum ditetapkan'}` : guideError || 'Status pengajuan, nilai, dan rencana studi Anda.'}</p>
      </div>
      {current && !open && <button type="button" className="primary" onClick={onStart}>{startLabel} <ArrowRight /></button>}
    </div>

    {loading ? <section className="workflow-card"><p className="dashboard-loading"><Loader2 className="spin" /> Memuat status pengajuan...</p></section>
      : error ? <section className="workflow-card"><p className="form-error" role="alert">{error}</p><div className="upload-actions"><button type="button" className="outline-button" onClick={onRetry}>Coba lagi</button></div></section>
      : current ? <SubmitCard submission={current} onChange={onChange} hidePlan />
      : <section className="workflow-card dashboard-empty">
        <h2>Belum ada pengajuan yang berjalan</h2>
        <p>Unggah KHS Anda untuk mendapatkan rekomendasi mata kuliah, lalu ajukan ke pembimbing akademik.</p>
        <button type="button" className="primary" onClick={onStart}>{startLabel} <ArrowRight /></button>
      </section>}

    <GradeSummary refreshKey={`${submission?.id}-${submission?.status}-${submission?.tahap}`} />

    {shownPlan?.rencana?.rencana_mk?.length ? <PlanSection submission={shownPlan} onClose={chosen ? () => setChosen(null) : undefined} /> : null}

    {(history.length > 0 || historyError) && <section className="workflow-card">
      <h2>Riwayat pengajuan</h2>
      {historyError && <p className="form-error" role="alert">{historyError} <button type="button" className="text-button" onClick={loadHistory}>Coba lagi</button></p>}
      <ul className="history-list">{history.map((item) => <li key={item.id}>
        <div><b>Semester {item.semester_target}</b><small>Diajukan {formatDate(item.diajukan_pada)}{item.catatan_dpa ? ` · Catatan: ${item.catatan_dpa}` : ''}</small></div>
        <SubmissionBadge submission={item} />
        <button type="button" className="outline-button" onClick={() => choose(item.id)} aria-label={`Lihat rencana pengajuan ${formatDate(item.diajukan_pada)}`}>Lihat rencana</button>
      </li>)}</ul>
      {chosen && !chosen.rencana?.rencana_mk?.length && <p role="status">Pengajuan tersebut belum memiliki rencana studi.</p>}
    </section>}
  </div>
}

function PlanSection({ submission, onClose }: { submission: Submission; onClose?: () => void }) {
  const plan = submission.rencana
  return <section className="result-section dashboard-section">
    <div className="result-section-head dashboard-section-head">
      <div>
        <h2>{submission.status === 'disetujui' ? 'Rencana studi disetujui' : 'Rencana studi'} · semester {submission.semester_target}</h2>
        <p>{plan?.total_sks ?? 0} SKS dari {plan?.rencana_mk?.length ?? 0} mata kuliah · diajukan {formatDate(submission.diajukan_pada)}</p>
      </div>
      <div className="dashboard-section-actions"><SubmissionBadge submission={submission} />{onClose && <button type="button" className="outline-button" onClick={onClose}>Tutup</button>}</div>
    </div>
    {plan?.rencana_mk?.map((course, index) => <div className="result-row" key={course.kode}><span>{index + 1}</span><div><b>{course.nama}</b><small>{course.kode}{course.sks ? ` · ${course.sks} SKS` : ''}</small></div><p>{course.alasan}</p></div>)}
    {plan?.peringatan?.map((warning) => <p className="dashboard-warning" key={warning}><AlertTriangle aria-hidden="true" /> {warning}</p>)}
  </section>
}

function GradeRow({ course }: { course: CourseGrade }) {
  return <li><div><b>{course.nama}</b><small>{course.kode}{course.sks !== null ? ` · ${course.sks} SKS` : ''}</small></div><span className="grade-chip" data-status={course.status} title={gradeStatus[course.status]}>{course.nilai}</span></li>
}

function GradeSummary({ refreshKey }: { refreshKey: string }) {
  const [data, setData] = useState<AcademicSummary | null>(null)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let active = true
    setError('')
    pengajuanService.academicSummary()
      .then((value) => { if (active) setData(value) })
      .catch((caught) => { if (active) setError(errorMessage(caught, 'Ringkasan nilai tidak dapat dimuat.')) })
    return () => { active = false }
  }, [refreshKey, attempt])

  if (error) return <section className="workflow-card"><h2>Ringkasan nilai</h2><p className="form-error" role="alert">{error}</p><div className="upload-actions"><button type="button" className="outline-button" onClick={() => setAttempt((value) => value + 1)}>Coba lagi</button></div></section>
  if (!data) return <section className="workflow-card"><p className="dashboard-loading"><Loader2 className="spin" /> Memuat ringkasan nilai...</p></section>
  const summary = data.ringkasan
  if (!summary || !data.sumber) return <section className="workflow-card"><h2>Ringkasan nilai</h2><p>Belum ada nilai untuk ditampilkan. Ringkasan muncul setelah KHS pada pengajuan Anda selesai dibaca.</p></section>

  const trend = summary.per_semester.filter((item) => item.semester > 0 && item.ip !== null)
  const stats = [
    { label: 'IPK', value: formatGpa(summary.ipk), note: 'Skala 4,00' },
    { label: 'SKS lulus', value: summary.sks_lulus, note: `dari ${summary.sks_total} SKS diambil` },
    { label: 'Mata kuliah', value: summary.jumlah_mk, note: `${summary.per_semester.filter((item) => item.semester > 0).length} semester terbaca` },
    { label: 'Perlu diulang', value: summary.perhatian.length, note: summary.perhatian.length ? 'Lihat daftar di bawah' : 'Tidak ada' },
  ]

  return <div className="grade-summary">
    <div className="dashboard-subheading"><h2>Ringkasan nilai</h2><p>Dari KHS pada pengajuan {formatDate(data.sumber.diajukan_pada)}.</p></div>
    <div className="stat-grid">{stats.map((stat) => <div className="stat-card" key={stat.label}><span>{stat.label}</span><b>{stat.value}</b><small>{stat.note}</small></div>)}</div>

    {summary.perhatian.length > 0 && <section className="workflow-card"><h2>Perlu perhatian</h2><ul className="grade-list">{summary.perhatian.map((course) => <GradeRow course={course} key={course.kode} />)}</ul></section>}

    <div className="chart-grid">
      {trend.length > 0 && <section className="workflow-card"><h2>IP per semester</h2><ul className="gpa-trend">{trend.map((item) => <li key={item.semester}><span>{formatGpa(item.ip)}</span><i style={{ height: `${Math.max(4, ((item.ip ?? 0) / 4) * 120)}px` }} aria-hidden="true" /><small>Smt {item.semester}</small></li>)}</ul></section>}
      <section className="workflow-card"><h2>Sebaran nilai</h2><ul className="grade-distribution">{summary.distribusi.map((item) => <li key={item.nilai}><span className="grade-chip">{item.nilai}</span><small>{item.jumlah} mata kuliah</small></li>)}</ul></section>
    </div>

    <section className="workflow-card"><h2>Nilai per semester</h2>{[...summary.per_semester].reverse().map((item, index) => <details className="semester-grades" key={item.semester} open={index === 0}><summary><b>{semesterLabel(item.semester)}</b><small>IP {formatGpa(item.ip)} · {item.sks} SKS · {item.mk.length} mata kuliah</small></summary><ul className="grade-list">{item.mk.map((course, position) => <GradeRow course={course} key={`${course.kode}-${position}`} />)}</ul></details>)}</section>
  </div>
}
