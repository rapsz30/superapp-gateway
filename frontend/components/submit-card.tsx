'use client'

import { useState } from 'react'
import { ChevronDown, Loader2 } from 'lucide-react'
import { SubmissionBadge } from '@/components/submission-badge'
import { errorMessage } from '@/src/lib/api'
import { pengajuanService, type Submission } from '@/src/services/pengajuan-service'
import type { CourseRecommendationResult } from '@/src/types/khs'

/**
 * Ajukan rencana studi ke dosen pembimbing akademik lewat proses AlurKerja, dan pantau statusnya. Yang dikirim berkas
 * KHS asli; server memakai bacaan dan rencana pratinjau yang disimpannya sendiri untuk berkas itu, jadi tidak ada yang
 * dibaca ulang. Nilai yang diubah di wizard ditandai untuk pembimbing.
 * Tanpa `result` (dasbor) kartu ini hanya menampilkan status pengajuan yang sudah ada.
 */
export function SubmitCard({ result, file = null, submission: latest, onChange, hidePlan = false }: { result?: CourseRecommendationResult; file?: File | null; submission: Submission | null; onChange: (value: Submission) => void; hidePlan?: boolean }) {
  // Pengajuan yang dibatalkan tidak ditampilkan sebagai status: hasil baru di layar belum diajukan.
  const submission = latest?.status === 'dibatalkan' ? null : latest
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [expanded, setExpanded] = useState(!!result)
  const advisor = result?.pembimbing_akademik?.nama_lengkap

  async function run(action: () => Promise<Submission>) {
    setBusy(true)
    setError('')
    try { onChange(await action()) } catch (caught) { setError(errorMessage(caught, 'Permintaan tidak dapat diproses.')) } finally { setBusy(false) }
  }

  const running = submission?.status === 'diajukan'
  const finished = submission && !running
  const bacaan = submission?.hasil_bacaan
  const rencana = submission?.rencana
  const collapsible = !!submission && !result
  const activeStep = submission?.langkah.find((step) => step.keadaan === 'aktif')
  const summaryStep = submission?.pesan_galat ? 'Proses memerlukan perhatian' : activeStep?.label ?? 'Semua tahapan selesai'
  return <section className={`workflow-card submit-card ${collapsible ? 'is-collapsible' : ''}`} aria-live="polite">
    <div className="submit-heading"><h2>{result ? 'Ajukan ke pembimbing akademik' : `Pengajuan rencana studi semester ${submission?.semester_target}`}</h2>{submission && <SubmissionBadge submission={submission} />}</div>
    {!submission && <p>Berkas KHS asli dan rencana studi dari preview ini akan dikirim bersama kepada {advisor ? <b>{advisor}</b> : 'pembimbing akademik Anda'}. Nilai yang Anda ubah akan ditandai agar diperiksa pembimbing.</p>}
    {collapsible && <div className="submit-collapse-row">
      <span className="submit-collapse-summary">{summaryStep}</span>
      <button type="button" className="submit-collapse-toggle" aria-expanded={expanded} aria-controls="submit-details" onClick={() => setExpanded((value) => !value)}>
        {expanded ? 'Sembunyikan detail' : 'Lihat progres'}<ChevronDown className={expanded ? 'expanded' : undefined} aria-hidden="true" />
      </button>
    </div>}
    {submission && <div id="submit-details" className="submit-details" hidden={collapsible && !expanded}>
      <div className="submit-advisor">
        <span>Pembimbing akademik</span>
        <b>{submission.dpa?.nama_lengkap ?? 'Belum ditentukan'}</b>
        {submission.jumlah_revisi > 0 && <small>Direvisi {submission.jumlah_revisi} kali</small>}
      </div>
      {(submission.catatan_dpa || (submission.panduan.versi_aktif_sekarang && submission.panduan.versi_aktif_sekarang > submission.panduan.versi)) && <div className="submit-note"><span>{submission.catatan_dpa ? 'Catatan pembimbing' : 'Informasi panduan'}</span><p>{submission.catatan_dpa || 'Panduan akademik sudah diperbarui sejak pengajuan ini dibuat. Pertimbangkan mengajukan ulang bila perlu.'}</p></div>}
      <ol className="submit-steps" aria-label="Progres pengajuan">{submission.langkah.map((step) => <li key={step.kunci} data-state={step.keadaan}><span className="submit-step-marker" aria-hidden="true">{step.keadaan === 'selesai' ? '✓' : step.keadaan === 'aktif' ? '•' : step.keadaan === 'galat' ? '!' : '○'}</span><div><b>{step.label}</b>{step.keterangan && <small>{step.keterangan}</small>}</div></li>)}</ol>
      {submission.pesan_galat && <p className="form-error" role="alert">Proses terhenti: {submission.pesan_galat}. Anda dapat membatalkan lalu mencoba lagi.</p>}
      {running && submission.tahap === 'periksa' && bacaan && <div className="info-callout"><span>
        <b>Periksa hasil bacaan KHS</b><br />
        IPK {bacaan.ipk ?? '-'} · SKS lulus {bacaan.sks_lulus ?? '-'} · perlu diulang: {bacaan.mk_ulang?.length ? bacaan.mk_ulang.join(', ') : 'tidak ada'}
      </span></div>}
      {!hidePlan && rencana?.rencana_mk && <details className="info-callout" open={!!result}><summary><b>Rencana studi dari sistem ({rencana.total_sks ?? 0} SKS)</b></summary><span>
        {rencana.rencana_mk.map((mk) => <span key={mk.kode}>{mk.kode} {mk.nama}{mk.sks ? ` (${mk.sks} SKS)` : ''}<br /></span>)}
        {rencana.peringatan?.map((w) => <small key={w}>⚠ {w}<br /></small>)}
      </span></details>}
    </div>}
    {error && <p className="form-error" role="alert">{error}</p>}
    <div className="upload-actions">
      {result && (!submission || finished) && <button type="button" className="primary" disabled={busy || !file} onClick={() => file && run(() => pengajuanService.submit(file, result.semester_target))}>{busy ? <><Loader2 className="spin" /> Mengirim...</> : submission ? 'Ajukan lagi' : 'Ajukan sekarang'}</button>}
      {running && submission.tahap === 'periksa' && <button type="button" className="primary" disabled={busy} onClick={() => run(() => pengajuanService.confirmCheck(submission.id))}>Data sudah benar, lanjutkan</button>}
      {running && <button type="button" className="outline-button" disabled={busy} onClick={() => run(() => pengajuanService.cancel(submission.id))}>Batalkan pengajuan</button>}
    </div>
    {result && !file && !submission && <small>Unggah ulang KHS dari awal untuk mengajukan.</small>}
  </section>
}
