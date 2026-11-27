'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { ArrowLeft, ArrowRight, Check, Download, FileText, Loader2, Plus, Trash2, Upload, X } from 'lucide-react'
import { BrandLogo, BrandedLoading } from '@/components/brand'
import { academicTargets, GRADE_POINTS, type AcademicTarget } from '@/src/lib/academic-targets'
import { errorMessage } from '@/src/lib/api'
import { GRADE_OPTIONS, khsService } from '@/src/services/khs-services'
import type { Submission } from '@/src/services/pengajuan-service'
import { usePengajuanSaya } from '@/src/hooks/use-pengajuan-saya'
import { SubmitCard } from '@/components/submit-card'
import { CourseDashboard } from '@/components/course-dashboard'
import type { CourseRecommendationResult, GuideInfo, KhsCourse, KhsStudent, NonCourseActivity } from '@/src/types/khs'

type Step = 1 | 2 | 3 | 4 | 5 | 6
const steps = ['Unggah KHS', 'Preview', 'Input nilai', 'Panduan akademik', 'Target akademik', 'Rekomendasi']
const gradeOptions = GRADE_OPTIONS
const activityOptions = ['Pengembangan Diri Qur\'ani', 'Student Soft Skill Development', 'Pelatihan Kepemimpinan dan Dakwah', 'Pendalaman Nilai Dasar Islam', 'Pelatihan Pengembangan Diri']
const initialStudent: KhsStudent = { name: '-', nim: '-', faculty: '-', program: '-', advisor: '-', credits: '-', gpa: '-' }
const totalSteps = 5
const MAX_KHS_FILE_SIZE = 10_000_000

function fileSizeInMb(bytes: number) {
  return `${(bytes / 1_000_000).toFixed(2)} MB`
}

export function CourseRecommendation({ studentFallback, studentId, startInWorkflow = false, onStart, onBackToDashboard }: { studentFallback?: Partial<KhsStudent>; studentId?: string; startInWorkflow?: boolean; onStart?: () => void; onBackToDashboard?: () => void }) {
  const [submission, setSubmission, saved] = usePengajuanSaya(studentId)
  // Mahasiswa mulai dari dasbor; selain mahasiswa tidak punya data pengajuan, jadi langsung ke langkah unggah.
  const [inWorkflow, setInWorkflow] = useState(startInWorkflow)
  const [step, setStep] = useState<Step>(1)
  const mobileStepperRef = useRef<HTMLDivElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [restartOpen, setRestartOpen] = useState(false)
  const [inputResetKey, setInputResetKey] = useState(0)
  const [analyzedFile, setAnalyzedFile] = useState<File | null>(null)
  // Sidik berkas dari server: menghubungkan hasil di layar dengan pengajuan nanti.
  const [fingerprint, setFingerprint] = useState<string | undefined>()
  const [guide, setGuide] = useState<GuideInfo | null>(null)
  const [guideLoading, setGuideLoading] = useState(false)
  const [guideError, setGuideError] = useState('')
  const [isProcessing, setIsProcessing] = useState(false)
  const [target, setTarget] = useState<AcademicTarget | null>(null)
  const [student, setStudent] = useState<KhsStudent>(initialStudent)
  const [grades, setGrades] = useState<KhsCourse[]>([])
  const [activities, setActivities] = useState<NonCourseActivity[]>([])
  const [error, setError] = useState('')
  const [result, setResult] = useState<CourseRecommendationResult | null>(null)
  const personalGuide = Boolean(guide?.panduanPribadi)
  const currentTitle = step === 1 ? 'Unggah KHS' : step === 2 ? 'Preview KHS' : step === 3 ? 'Input dan edit nilai' : step === 4 ? (personalGuide ? 'Panduan akademik Anda' : 'Panduan akademik prodi Anda') : step === 5 ? 'Target Akademik' : 'Rekomendasi mata kuliah'
  const currentDescription = step === 1 ? 'Pastikan file KHS Anda dalam format PDF.' : step === 2 ? 'Pastikan seluruh data sudah benar sebelum melanjutkan.' : step === 3 ? 'Perbaiki hasil ekstraksi KHS sebelum lanjut ke rekomendasi.' : step === 4 ? (personalGuide ? 'Unggah panduan akademik Anda (PDF). Rekomendasi disusun dari berkas yang Anda unggah.' : 'Rekomendasi disusun dari panduan akademik resmi program studi Anda. Anda tidak perlu mengunggahnya.') : step === 5 ? 'Pilih prioritas studi Anda untuk hasil rekomendasi yang lebih terpersonalisasi.' : 'Rekomendasi disusun berdasarkan data akademik dan target Anda.'

  function upload(input: HTMLInputElement) {
    const selected = input.files?.[0]
    if (!selected) return
    const isPdf = selected.type === 'application/pdf' || selected.name.toLowerCase().endsWith('.pdf')
    if (!isPdf) { setFile(null); setError('Format file tidak didukung. Pilih dokumen PDF.'); input.value = ''; return }
    if (selected.size > MAX_KHS_FILE_SIZE) { setFile(null); setError(`Ukuran file ${fileSizeInMb(selected.size)}. Maksimal 10 MB.`); input.value = ''; return }
    setError('')
    setFile(selected)
    setAnalyzedFile(null)
    setStudent(initialStudent)
    setGrades([])
    setResult(null)
    input.value = ''
  }

  async function analyzeFile() {
    if (!file) return
    setError('')
    setStep(2)
    setIsProcessing(true)
    try {
      const response = await khsService.processDocument(file, studentFallback)
      setAnalyzedFile(file)
      setFingerprint(response.fingerprint)
      setStudent(response.student)
      setGrades(response.courses)
      setResult(null)
      if (response.warning) setError(response.warning)
      else if (!response.courses.length) setError('Tidak ada mata kuliah yang terbaca dari KHS. Periksa file Anda.')
    } catch (caught) {
      setAnalyzedFile(null)
      setError(errorMessage(caught, 'File tidak dapat diproses.'))
    } finally {
      setIsProcessing(false)
    }
  }

  async function generate() {
    setIsProcessing(true)
    try {
      setResult(await khsService.recommend(student, grades, fingerprint))
      setStep(6)
    } catch (caught) {
      setError(errorMessage(caught, 'Rekomendasi tidak dapat dibuat. Coba lagi.'))
    } finally {
      setIsProcessing(false)
    }
  }

  async function next() {
    if (step === 1) {
      if (!file) { setError('Pilih file KHS terlebih dahulu.'); return }
      if (analyzedFile !== file) { await analyzeFile(); return }
    }
    if (step === 2 && (!analyzedFile || !grades.length)) {
      setError('Tunggu sampai analisis KHS selesai dan pastikan ada nilai yang terbaca.')
      return
    }
    if (step === 3) {
      if (grades.length === 0) { setError('Minimal harus ada 1 mata kuliah.'); return }
      if (grades.some((course) => !course.name.trim())) { setError('Lengkapi nama semua mata kuliah atau hapus baris yang kosong.'); return }
    }
    if (step === 5 && !target) { setError('Silakan pilih target akademik terlebih dahulu.'); return }
    setError('')
    if (step === 5) { await generate(); return }
    setStep((value) => Math.min(6, value + 1) as Step)
  }
  function back() { setError(''); setStep((value) => Math.max(1, value - 1) as Step) }

  // Panduan prodi dimuat saat langkah 4 dibuka. Satu kali per sesi: prodi mahasiswa tidak berubah.
  async function loadGuide() {
    setGuideLoading(true)
    setGuideError('')
    try {
      setGuide(await khsService.getGuide())
    } catch (caught) {
      setGuide(null)
      setGuideError(errorMessage(caught, 'Panduan akademik tidak dapat dimuat.'))
    } finally {
      setGuideLoading(false)
    }
  }
  useEffect(() => {
    if (step === 4 && !guide && !guideLoading && !guideError) void loadGuide()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step])

  const totalCredits = useMemo(() => grades.reduce((sum, course) => sum + course.credits, 0), [grades])
  const progress = Math.min(step, totalSteps) / totalSteps * 100

  useEffect(() => {
    const stepper = mobileStepperRef.current
    if (!stepper || step > totalSteps) return

    const keepActiveStepVisible = () => {
      if (window.matchMedia('(min-width: 701px)').matches) return
      const activeStep = stepper.querySelector<HTMLElement>('[data-current="true"]')
      if (!activeStep) return
      const activeStepLeft = activeStep.getBoundingClientRect().left - stepper.getBoundingClientRect().left + stepper.scrollLeft
      const centeredLeft = activeStepLeft - (stepper.clientWidth - activeStep.clientWidth) / 2
      const maxLeft = stepper.scrollWidth - stepper.clientWidth
      stepper.scrollTo({ left: Math.max(0, Math.min(centeredLeft, maxLeft)), behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' })
    }

    keepActiveStepVisible()
    window.addEventListener('resize', keepActiveStepVisible)
    return () => window.removeEventListener('resize', keepActiveStepVisible)
  }, [step])

  function resetWorkflow() {
    setFile(null)
    setResult(null)
    setAnalyzedFile(null)
    setInputResetKey((value) => value + 1)
    setIsProcessing(false)
    setTarget(null)
    setStudent(initialStudent)
    setGrades([])
    setActivities([])
    setError('')
    setStep(1)
    setRestartOpen(false)
  }

  if (studentId && !inWorkflow) {
    return <CourseDashboard studentId={studentId} name={studentFallback?.name} submission={submission} loading={saved.loading} error={saved.error} onRetry={saved.reload} onChange={setSubmission} started={step > 1 || !!file} onStart={() => { setInWorkflow(true); onStart?.() }} />
  }

  return <div className="page-content course-page">
    {studentId && <button type="button" className="back-link" onClick={() => onBackToDashboard ? onBackToDashboard() : setInWorkflow(false)}><ArrowLeft /> Kembali ke ringkasan</button>}
    {step < 6 && <div className="course-heading"><div><h1>{currentTitle}</h1><p>{currentDescription}</p></div><span className="step-label">Langkah {step} dari 5</span></div>}
    {step < 6 && <div className="workflow-stepper desktop-workflow-stepper" aria-label="Progress rekomendasi mata kuliah">{steps.slice(0, 5).map((label, index) => <div className={`workflow-step ${index + 1 < step ? 'done' : ''} ${index + 1 === step ? 'current' : ''}`} key={label}><span>{index + 1 < step ? <Check /> : index + 1}</span><b>{label}</b></div>)}</div>}
    {step < 6 && <div ref={mobileStepperRef} className="workflow-stepper mobile-workflow-stepper" aria-label="Progress rekomendasi mata kuliah">{steps.slice(0, totalSteps).map((label, index) => <div className={`workflow-step ${index + 1 < step ? 'done' : ''} ${index + 1 === step ? 'current' : ''}`} data-current={index + 1 === step || undefined} key={label}><span>{index + 1 < step ? <Check /> : index + 1}</span><b>{label}</b></div>)}</div>}
    {step === 1 && <UploadStep inputKey={inputResetKey} progress={progress} file={file} error={error} onUpload={upload} onRemove={() => { setFile(null); setAnalyzedFile(null); setGrades([]); setStudent(initialStudent); setResult(null); setError('') }} />}
    {step === 2 && <PreviewStep progress={progress} file={file} isProcessing={isProcessing} student={student} grades={grades} />}
    {step === 3 && <EditStep progress={progress} grades={grades} setGrades={setGrades} activities={activities} setActivities={setActivities} totalCredits={totalCredits} />}
    {step === 4 && <GuideStep progress={progress} guide={guide} loading={guideLoading} error={guideError} onRetry={() => void loadGuide()} onUploaded={(g) => setGuide(g)} />}
    {step === 5 && <TargetStep progress={progress} target={target} setTarget={setTarget} />}
    {step === 6 && target && result && <ResultsStep student={student} target={target} grades={grades} activities={activities} result={result} file={file} submission={submission} onSubmissionChange={setSubmission} />}
    {error && <p className="form-error" role="alert">{error}</p>}
    <div className="workflow-actions" role="group" aria-label="Navigasi langkah rekomendasi">{step > 1 && step < 6 && <button className="outline-button" onClick={back}>Kembali</button>}{step < 6 ? <button className="primary" onClick={next} disabled={isProcessing || step === 1 && !file || step === 2 && (!analyzedFile || !grades.length) || step === 4 && !guide?.panduanId}>{isProcessing ? <><Loader2 className="spin" /> Sedang memproses...</> : <>{step === 1 ? 'Lanjut ke preview' : step === 5 ? 'Lihat hasil rekomendasi' : step === 3 ? 'Simpan dan lanjut' : 'Lanjut'}</>}</button> : <button className="primary" onClick={() => setRestartOpen(true)}>Mulai ulang</button>}</div>{restartOpen && <RestartDialog onCancel={() => setRestartOpen(false)} onConfirm={resetWorkflow} />}
    {isProcessing && step === 5 && <RecommendationLoadingModal />}
  </div>
}

function UploadStep({ inputKey, progress, file, error, onUpload, onRemove }: { inputKey: number; progress: number; file: File | null; error: string; onUpload: (input: HTMLInputElement) => void; onRemove: () => void }) {
  const inputRef = useRef<HTMLInputElement>(null)
  const openPicker = () => inputRef.current?.click()
  return <section className="workflow-card"><div className="card-topline"><b>Langkah 1 dari 5</b><span>Unggah KHS</span></div><div className="progress-line"><i style={{ width: `${progress}%` }} /></div><h2>Unggah KHS</h2><p>Pilih file KHS terlebih dahulu. Sistem akan memeriksa dan menganalisisnya pada langkah Preview.</p><div className={`upload-zone ${file ? 'uploaded' : ''}`} role="button" tabIndex={0} onClick={openPicker} onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); openPicker() } }}><input key={inputKey} ref={inputRef} type="file" accept="application/pdf" onChange={(event) => onUpload(event.currentTarget)} /><div className="upload-icon">{file ? <Check /> : <Upload />}</div><strong>{file ? file.name : 'Klik untuk memilih file KHS'}</strong><small>{file ? `${fileSizeInMb(file.size)} · PDF · siap ditinjau` : 'Format PDF · Maksimal 10 MB'}</small><div className="upload-actions"><button type="button" className="primary small" onClick={(event) => { event.stopPropagation(); openPicker() }}>{file ? 'Ganti file' : 'Pilih file'}</button>{file && <button type="button" className="outline-button small" onClick={(event) => { event.stopPropagation(); onRemove() }}><X /> Hapus</button>}</div></div>{error && <p className="form-error">{error}</p>}</section>
}

function PreviewStep({ progress, file, isProcessing, student, grades }: { progress: number; file: File | null; isProcessing: boolean; student: KhsStudent; grades: KhsCourse[] }) { return <section className="workflow-card"><div className="card-topline"><b>Langkah 2 dari 5</b><span>Preview & analisis</span></div><div className="progress-line"><i style={{ width: `${progress}%` }} /></div>{isProcessing ? <div className="processing-state"><BrandedLoading message="Sedang menganalisis KHS..." /><small>{file ? `${file.name} · ${fileSizeInMb(file.size)}` : 'Membaca dokumen KHS'}</small><small>Membaca identitas mahasiswa dan mengekstrak daftar nilai. Proses ini bisa memakan waktu hingga satu menit.</small></div> : <><h2>Hasil preview KHS</h2><p>Periksa identitas dan daftar nilai berikut. Jika ada peringatan, kembali dan unggah KHS yang benar.</p><div className="student-summary">{Object.entries(student).map(([key, value]) => <div key={key}><span>{key}</span><b>{value}</b></div>)}</div><h2>Daftar mata kuliah</h2><div className="academic-table-scroll"><div className="academic-table"><div className="table-row table-head"><span>No</span><span>Kode</span><span>Mata kuliah</span><span>SKS</span><span>Nilai</span></div>{grades.map((course, index) => <div className="table-row" key={`${course.code}-${index}`}><span>{index + 1}</span><span>{course.code}</span><b>{course.name}</b><span>{course.credits}</span><strong>{course.grade}</strong></div>)}</div></div></>}</section> }

function EditStep({ progress, grades, setGrades, activities, setActivities, totalCredits }: { progress: number; grades: KhsCourse[]; setGrades: (value: KhsCourse[]) => void; activities: NonCourseActivity[]; setActivities: (value: NonCourseActivity[]) => void; totalCredits: number }) {
  const [activity, setActivity] = useState<NonCourseActivity>({ name: '', group: '', year: '2026', grade: '' })
  const [deleteTarget, setDeleteTarget] = useState<{ type: 'course' | 'activity'; index: number; label: string } | null>(null)
  const gradePoints = GRADE_POINTS
  const estimatedGpa = grades.length ? (grades.reduce((sum, course) => sum + (gradePoints[course.grade] ?? 0) * course.credits, 0) / Math.max(totalCredits, 1)).toFixed(2) : '0.00'

  function addCourse() { setGrades([...grades, { code: '', name: '', credits: 3, grade: '' }]) }
  function addActivity() {
    if (!activity.name || !activity.grade) return
    if (activities.some((item) => item.name === activity.name)) return
    setActivities([...activities, activity])
    setActivity({ name: '', group: '', year: '2026', grade: '' })
  }

  function confirmDelete() {
    if (!deleteTarget) return
    if (deleteTarget.type === 'course') setGrades(grades.filter((_, index) => index !== deleteTarget.index))
    else setActivities(activities.filter((_, index) => index !== deleteTarget.index))
    setDeleteTarget(null)
  }

  return <>
    <section className="workflow-card"><div className="card-topline"><b>Langkah 3 dari 5</b><span>Input nilai</span></div><div className="progress-line"><i style={{ width: `${progress}%` }} /></div><div className="edit-table">{grades.map((course, index) => <div className="edit-row" key={index}><span>{index + 1}</span><input aria-label={`Kode ${course.name}`} value={course.code} onChange={(event) => setGrades(grades.map((item, itemIndex) => itemIndex === index ? { ...item, code: event.target.value } : item))} /><input aria-label={`Mata kuliah ${course.code}`} value={course.name} onChange={(event) => setGrades(grades.map((item, itemIndex) => itemIndex === index ? { ...item, name: event.target.value } : item))} /><input aria-label={`SKS ${course.name}`} type="number" min="1" value={course.credits} onChange={(event) => setGrades(grades.map((item, itemIndex) => itemIndex === index ? { ...item, credits: Number(event.target.value) } : item))} /><select aria-label={`Nilai ${course.name}`} value={course.grade} onChange={(event) => setGrades(grades.map((item, itemIndex) => itemIndex === index ? { ...item, grade: event.target.value } : item))}><option value="" disabled>Pilih nilai</option>{gradeOptions.map((grade) => <option key={grade} value={grade}>{grade}</option>)}</select><button type="button" className="delete-course" aria-label={`Hapus ${course.name}`} onClick={() => setDeleteTarget({ type: 'course', index, label: course.name })}><Trash2 /></button></div>)}</div><button type="button" className="outline-button add-course-button" onClick={addCourse}><Plus /> Tambah mata kuliah</button><p className="table-summary"><b>{totalCredits} SKS</b> dari {grades.length} mata kuliah, perkiraan IPK <b>{estimatedGpa}</b>.</p></section>
    <section className="workflow-card activity-card original-activity-card"><h2>Kegiatan non-mata kuliah</h2><p>Tambahkan nilai kegiatan di luar mata kuliah jika ada</p><div className="activity-form-grid"><label>Nama kegiatan<select value={activity.name} onChange={(event) => setActivity({ ...activity, name: event.target.value })}><option value="">Pilih kegiatan</option>{activityOptions.map((option) => <option key={option} value={option}>{option}</option>)}</select></label><label>Kelas/Kelompok<input value={activity.group} onChange={(event) => setActivity({ ...activity, group: event.target.value })} placeholder="Contoh: PTA-N" /></label><label>Tahun (opsional)<input value={activity.year} onChange={(event) => setActivity({ ...activity, year: event.target.value })} placeholder="2026" /></label><label>Nilai akhir<select value={activity.grade} onChange={(event) => setActivity({ ...activity, grade: event.target.value })}><option value="">Pilih nilai</option>{gradeOptions.map((grade) => <option key={grade} value={grade}>{grade}</option>)}</select></label></div><div className="activity-add-row"><button className="primary activity-add-button" type="button" onClick={addActivity}><Plus /> Tambah kegiatan</button></div><div className="activity-list-heading"><b>Daftar kegiatan</b><span>Total: {activities.length}</span></div><div className="activity-table"><div className="activity-table-head"><span>No</span><span>Kegiatan</span><span>Kelas/Kelompok</span><span>Nilai akhir</span><span>Tahun</span><span>Aksi</span></div>{activities.length === 0 ? <div className="activity-empty">Belum ada data.</div> : activities.map((item, index) => <div className="activity-table-row" key={`${item.name}-${index}`}><span>{index + 1}</span><b>{item.name}</b><span>{item.group || '-'}</span><span>{item.grade}</span><span>{item.year || '-'}</span><button type="button" className="delete-course" aria-label={`Hapus ${item.name}`} onClick={() => setDeleteTarget({ type: 'activity', index, label: item.name })}><Trash2 /></button></div>)}</div></section>
    {deleteTarget && <ConfirmDeleteDialog label={deleteTarget.label} onCancel={() => setDeleteTarget(null)} onConfirm={confirmDelete} />}
  </>
}

function RestartDialog({ onCancel, onConfirm }: { onCancel: () => void; onConfirm: () => void }) { return <div className="dialog-backdrop" role="presentation" onMouseDown={onCancel}><div className="confirm-dialog" role="alertdialog" aria-modal="true" aria-labelledby="restart-dialog-title" aria-describedby="restart-dialog-description" onMouseDown={(event) => event.stopPropagation()}><button type="button" className="dialog-close" aria-label="Tutup dialog" onClick={onCancel}><X /></button><div className="dialog-icon"><ArrowRight /></div><h2 id="restart-dialog-title">Mulai ulang proses rekomendasi?</h2><p id="restart-dialog-description">Seluruh data yang telah diunggah dan diinput akan dihapus. Apakah Anda yakin ingin melanjutkan?</p><div className="dialog-actions"><button type="button" className="outline-button" onClick={onCancel}>Batal</button><button type="button" className="danger-button" onClick={onConfirm}>Ya, mulai ulang</button></div></div></div> }

function ConfirmDeleteDialog({ label, onCancel, onConfirm }:  { label: string; onCancel: () => void; onConfirm: () => void }) { return <div className="dialog-backdrop" role="presentation" onMouseDown={onCancel}><div className="confirm-dialog" role="alertdialog" aria-modal="true" aria-labelledby="delete-dialog-title" aria-describedby="delete-dialog-description" onMouseDown={(event) => event.stopPropagation()}><button type="button" className="dialog-close" aria-label="Tutup dialog" onClick={onCancel}><X /></button><div className="dialog-icon"><Trash2 /></div><h2 id="delete-dialog-title">Hapus data?</h2><p id="delete-dialog-description">Apakah Anda yakin ingin menghapus <b>{label}</b>? Data yang dihapus tidak dapat dikembalikan.</p><div className="dialog-actions"><button type="button" className="outline-button" onClick={onCancel}>Batal</button><button type="button" className="danger-button" onClick={onConfirm}>Ya, hapus</button></div></div></div> }

function GuideStep({ progress, guide, loading, error, onRetry, onUploaded }: { progress: number; guide: GuideInfo | null; loading: boolean; error: string; onRetry: () => void; onUploaded: (guide: GuideInfo) => void }) {
  const [opening, setOpening] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [openError, setOpenError] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)
  const pribadi = Boolean(guide?.panduanPribadi)
  async function openFile() {
    if (!guide?.panduanId) return
    setOpening(true)
    setOpenError('')
    try { await khsService.openGuideFile(guide.panduanId) } catch (caught) { setOpenError(errorMessage(caught, 'Berkas panduan tidak dapat dibuka.')) } finally { setOpening(false) }
  }
  async function onPick(input: HTMLInputElement) {
    const file = input.files?.[0]
    input.value = ''
    if (!file) return
    if (!(file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf'))) {
      setOpenError('Berkas harus berupa PDF.')
      return
    }
    setUploading(true)
    setOpenError('')
    try { onUploaded(await khsService.uploadPersonalGuide(file)) } catch (caught) { setOpenError(errorMessage(caught, 'Unggah panduan gagal.')) } finally { setUploading(false) }
  }
  return (
    <section className="workflow-card">
      <div className="card-topline"><b>Langkah 4 dari 5</b><span>Panduan akademik</span></div>
      <div className="progress-line"><i style={{ width: `${progress}%` }} /></div>
      <h2>{pribadi ? 'Panduan akademik Anda' : 'Panduan akademik prodi Anda'}</h2>
      {loading ? (
        <div className="processing-state"><Loader2 className="spin" /><strong>Memuat panduan akademik...</strong></div>
      ) : guide?.panduanId ? (
        <>
          <p>{pribadi ? 'Rekomendasi mengikuti panduan yang Anda unggah.' : 'Rekomendasi akan mengikuti aturan di panduan ini.'}</p>
          <div className="info-callout">
            <FileText />
            <span>
              <b>{guide.title}</b><br />
              {pribadi ? 'Panduan pribadi' : <>Program studi {guide.program}{guide.faculty ? `, ${guide.faculty}` : ''}</>}
              {' · '}Versi {guide.version}
              {guide.effectiveFrom ? ` · berlaku mulai ${new Date(guide.effectiveFrom).toLocaleDateString('id-ID', { day: 'numeric', month: 'long', year: 'numeric' })}` : ''}
              {guide.advisorName ? <><br />Pembimbing akademik: {guide.advisorName}</> : null}
            </span>
          </div>
          <div className="upload-actions">
            <button type="button" className="outline-button small" onClick={openFile} disabled={opening}>{opening ? 'Membuka...' : 'Lihat panduan (PDF)'}</button>
            {pribadi && (
              <>
                <input ref={inputRef} type="file" accept="application/pdf,.pdf" hidden onChange={(e) => void onPick(e.currentTarget)} />
                <button type="button" className="outline-button small" onClick={() => inputRef.current?.click()} disabled={uploading}>{uploading ? 'Mengunggah...' : 'Ganti panduan'}</button>
              </>
            )}
          </div>
          {openError && <p className="form-error" role="alert">{openError}</p>}
        </>
      ) : pribadi ? (
        <>
          <p>Anda belum mengunggah panduan akademik. Unggah PDF panduan Anda untuk melanjutkan.</p>
          <input ref={inputRef} type="file" accept="application/pdf,.pdf" hidden onChange={(e) => void onPick(e.currentTarget)} />
          <div className="upload-actions">
            <button type="button" className="primary small" onClick={() => inputRef.current?.click()} disabled={uploading}>{uploading ? 'Mengunggah...' : 'Unggah panduan (PDF)'}</button>
            <button type="button" className="outline-button small" onClick={onRetry}>Muat ulang</button>
          </div>
          {openError && <p className="form-error" role="alert">{openError}</p>}
        </>
      ) : (
        <>
          <p className="form-error" role="alert">{error || 'Panduan akademik tidak tersedia.'}</p>
          <div className="upload-actions"><button type="button" className="outline-button small" onClick={onRetry}>Coba lagi</button></div>
        </>
      )}
    </section>
  )
}

function TargetStep({ progress, target, setTarget }: { progress: number; target: AcademicTarget | null; setTarget: (value: AcademicTarget) => void }) { return <section className="workflow-card"><div className="card-topline"><b>Langkah 5 dari 5</b><span>Target akademik</span></div><div className="progress-line"><i style={{ width: `${progress}%` }} /></div><h2>Apa prioritas studi Anda?</h2><div className="target-options">{academicTargets.map((option) => <label className={`target-option ${target === option.id ? 'selected' : ''}`} key={option.id}><input type="radio" name="target" checked={target === option.id} onChange={() => setTarget(option.id)} /><span className="radio-dot" /><div><b>{option.title}</b><p>{option.description}</p></div><strong>Nilai minimal<br />{option.minimum}</strong></label>)}</div></section> }

function RecommendationLoadingModal() {
  return <div className="recommendation-loading-backdrop" role="presentation">
    <div className="recommendation-loading-modal" role="dialog" aria-modal="true" aria-labelledby="recommendation-loading-title" aria-describedby="recommendation-loading-description">
      <div className="recommendation-loading-icon"><BrandLogo variant="mark" className="recommendation-loading-logo" /></div>
      <h2 id="recommendation-loading-title">Sedang menyusun rekomendasi</h2>
      <p id="recommendation-loading-description">Kami sedang mencocokkan nilai, panduan akademik, dan target studi Anda.</p>
      <div className="recommendation-loading-progress" aria-hidden="true"><i /></div>
      <small>Proses ini dapat memerlukan waktu beberapa saat. Jangan tutup halaman ini.</small>
    </div>
  </div>
}

function ResultsStep({ student, target, grades, activities, result, file, submission, onSubmissionChange }: { student: KhsStudent; target: AcademicTarget; grades: KhsCourse[]; activities: NonCourseActivity[]; result: CourseRecommendationResult; file: File | null; submission: Submission | null; onSubmissionChange: (value: Submission) => void }) {
  const targetOption = academicTargets.find((item) => item.id === target)
  const creditsByCode = new Map(grades.map((course) => [course.code.toUpperCase(), course.credits]))
  const nextCourses = result.rekomendasi_semester_depan.filter((item) => item.jenis === 'baru').map((item) => ({ name: item.nama, code: item.kode, credits: item.sks ? `${item.sks} SKS` : undefined, note: item.alasan }))
  const attentionCourses = result.evaluasi_nilai.map((item) => { const sks = creditsByCode.get(item.kode.toUpperCase()); return { name: item.nama, code: item.kode, credits: sks ? `${sks} SKS` : undefined, note: item.saran, grade: item.nilai } })
  const belowTargetCandidates = grades.map((course) => ({ name: course.name, code: course.code, credits: `${course.credits} SKS`, grade: course.grade }))
  return <div className="results-stack">
    <div className="result-hero result-hero-with-action"><div><h2>Halo, {student.name}</h2><p>Mahasiswa {student.program}. Sudah menempuh {student.credits} dengan IPK kumulatif {student.gpa}. Rekomendasi ini disusun untuk semester {result.semester_target}.</p>{result.ringkasan && <p>{result.ringkasan}</p>}{result.panduan && <p><small>Dasar rekomendasi: {result.panduan.pribadi ? `Panduan yang Anda unggah, versi ${result.panduan.versi}` : `Panduan akademik Prodi ${result.panduan.prodi.nama}, versi ${result.panduan.versi}`}.</small></p>}{result.peringatan?.map((warning) => <p className="form-error" role="status" key={warning}>{warning}</p>)}</div><div className="result-actions"><button type="button" className="outline-button export-pdf-button" onClick={() => window.print()}><Download /> Export ke PDF</button></div></div>
    <SubmitCard result={result} file={file} submission={submission} onChange={onSubmissionChange} />
    <ResultSection title="Rekomendasi berdasarkan panduan akademik" description={`Mata kuliah semester ${result.semester_target} sesuai panduan prodi.`} tone="blue" items={nextCourses} />
    <ResultSection title="Mata kuliah yang perlu diulang" description="Nilai pada mata kuliah berikut belum memenuhi ketentuan akademik. Prioritaskan untuk ditinjau kembali." tone="purple" items={attentionCourses} />
    <TargetResultSection targetTitle={targetOption?.title || ''} minimum={targetOption?.minimum || ''} items={belowTargetCandidates} />
    <ActivityResultSection activities={activities} />
  </div>
}
function ActivityResultSection({ activities }: { activities: NonCourseActivity[] }) { return <section className="result-section activity-result-section"><div className="result-section-head"><h2>Kegiatan non-mata kuliah</h2><p>Aktivitas akademik di luar mata kuliah yang Anda masukkan.</p></div>{activities.length === 0 ? <div className="activity-result-empty">Belum ada kegiatan non-mata kuliah yang ditambahkan.</div> : <div className="activity-result-table"><div className="activity-result-row activity-result-head"><span>Kode</span><span>Kegiatan</span><span>Nilai akhir</span></div>{activities.map((activity) => <div className="activity-result-row" key={`${activity.name}-${activity.year}`}><b>{activityCode(activity.name)}</b><span>{activity.name}</span><strong>{activity.grade || 'Belum ada'}</strong></div>)}</div>}</section> }
function activityCode(name: string) { const codes: Record<string, string> = { "Pengembangan Diri Qur'ani": 'PDQ', 'Student Soft Skill Development': 'S3D', 'Pelatihan Kepemimpinan dan Dakwah': 'PKD', 'Pendalaman Nilai Dasar Islam': 'PNDI', 'Pelatihan Pengembangan Diri': 'PPD' }; return codes[name] || '—' }
function ResultSection({ title, description, tone, items }: { title: string; description: string; tone: string; items: Array<{ name: string; code: string; credits?: string; note?: string; grade?: string }> }) { return <section className={`result-section ${tone}`}><div className="result-section-head"><h2>{title}</h2><p>{description}</p></div>{items.length === 0 && <div className="activity-result-empty">Tidak ada data untuk bagian ini.</div>}{items.map((item, index) => <div className="result-row" key={`${item.code}-${index}`}><span>{index + 1}</span><div><b>{item.name}</b><small>{item.code} {item.credits && `· ${item.credits}`}</small></div><p>{item.note || 'Nilai saat ini'}</p>{item.grade && <strong>{item.grade}</strong>}</div>)}</section> }
function TargetResultSection({ targetTitle, minimum, items }: { targetTitle: string; minimum: string; items: Array<{ name: string; code: string; credits?: string; grade?: string }> }) { const points = GRADE_POINTS; const minimumPoints = points[minimum] ?? 3; const belowTarget = items.filter((item) => (points[item.grade || ''] ?? 0) < minimumPoints); return <section className="result-section green"><div className="result-section-head"><h2>Langkah menuju target</h2><p>Tingkatkan nilai pada mata kuliah berikut untuk mendukung target akademik Anda.</p><span className="target-badge">Target dipilih: {targetTitle} · minimal {minimum}</span></div><div className="target-result-head"><span>Nilai di Bawah Target</span><span>Nilai saat ini</span></div>{belowTarget.length ? belowTarget.map((item, index) => <div className="result-row target-result-row" key={item.name}><span>{index + 1}</span><div><b>{item.name}</b><small>{item.code} {item.credits && `· ${item.credits}`}</small></div><span className="target-current-grade">{item.grade || 'Belum ada'}</span></div>) : <div className="activity-result-empty">Tidak ada mata kuliah di bawah target.</div>}</section> }
