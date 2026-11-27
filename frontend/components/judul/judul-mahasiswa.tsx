'use client'

import { useEffect, useState } from 'react'
import { ArrowRight, Archive, BookOpenCheck, ChevronLeft, ChevronRight, FileText, Loader2, MessageCircle, MessageSquareText } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { errorMessage } from '@/src/lib/api'
import { judulService, type ThesisChatSummary, type ThesisMine, type ThesisRecommendationSummary, type ThesisSubmission } from '@/src/services/judul-service'

const PAGE_SIZE = 5

function tanggal(value: string) {
  return new Date(value).toLocaleDateString('id-ID', { dateStyle: 'medium' })
}

function statusLabel(submission: ThesisSubmission) {
  if (submission.status === 'disetujui') return 'Disetujui'
  if (submission.status === 'dibatalkan') return 'Dibatalkan'
  if (submission.tahap === 'perbaikan') return 'Perlu Anda perbaiki'
  return 'Menunggu pembimbing'
}

function statusTone(submission: ThesisSubmission) {
  if (submission.status === 'disetujui') return 'success'
  if (submission.status === 'dibatalkan') return 'neutral'
  if (submission.tahap === 'perbaikan') return 'warning'
  return 'info'
}

export function JudulMahasiswa() {
  const router = useRouter()
  const [mine, setMine] = useState<ThesisMine | null>(null)
  const [obrolan, setObrolan] = useState<ThesisChatSummary[]>([])
  const [riwayat, setRiwayat] = useState<ThesisRecommendationSummary[]>([])
  const [obrolanTotal, setObrolanTotal] = useState(0)
  const [riwayatTotal, setRiwayatTotal] = useState(0)
  const [obrolanPage, setObrolanPage] = useState(1)
  const [riwayatPage, setRiwayatPage] = useState(1)
  const [historyLoading, setHistoryLoading] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [cancelDialogOpen, setCancelDialogOpen] = useState(false)

  async function load() {
    setLoading(true)
    setError('')
    try {
      const [mineResult, daftarObrolan, daftarRiwayat] = await Promise.all([
        judulService.saya(),
        judulService.daftarObrolan(1, PAGE_SIZE),
        judulService.daftarRiwayat(1, PAGE_SIZE),
      ])
      setMine(mineResult)
      setObrolan(daftarObrolan.data)
      setObrolanTotal(daftarObrolan.total)
      setObrolanPage(1)
      setRiwayat(daftarRiwayat.data)
      setRiwayatTotal(daftarRiwayat.total)
      setRiwayatPage(1)
    } catch (caught) {
      setError(errorMessage(caught, 'Data judul tugas akhir tidak dapat dimuat.'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [])

  // Selama menunggu keputusan, status disegarkan diam-diam (tanpa indikator memuat), juga saat tab dibuka lagi.
  useEffect(() => {
    if (mine?.pengajuan?.status !== 'diajukan') return
    let aktif = true
    const segarkan = () => {
      if (document.visibilityState !== 'visible') return
      judulService.saya().then((hasil) => { if (aktif) setMine(hasil) }).catch(() => undefined)
    }
    const timer = window.setInterval(segarkan, 10_000)
    document.addEventListener('visibilitychange', segarkan)
    return () => { aktif = false; window.clearInterval(timer); document.removeEventListener('visibilitychange', segarkan) }
  }, [mine?.pengajuan?.id, mine?.pengajuan?.status])

  async function pindahObrolan(page: number) {
    setHistoryLoading(true)
    setError('')
    try {
      const result = await judulService.daftarObrolan(page, PAGE_SIZE)
      setObrolan(result.data)
      setObrolanTotal(result.total)
      setObrolanPage(result.halaman)
    } catch (caught) {
      setError(errorMessage(caught, 'Daftar obrolan tidak dapat dimuat.'))
    } finally {
      setHistoryLoading(false)
    }
  }

  async function pindahRiwayat(page: number) {
    setHistoryLoading(true)
    setError('')
    try {
      const result = await judulService.daftarRiwayat(page, PAGE_SIZE)
      setRiwayat(result.data)
      setRiwayatTotal(result.total)
      setRiwayatPage(result.halaman)
    } catch (caught) {
      setError(errorMessage(caught, 'Arsip rekomendasi tidak dapat dimuat.'))
    } finally {
      setHistoryLoading(false)
    }
  }

  async function batalkan() {
    if (!mine?.pengajuan) return
    setCancelDialogOpen(false)
    setSaving(true)
    setError('')
    try {
      const result = await judulService.batalkan(mine.pengajuan.id)
      setMine((value) => value ? { ...value, pengajuan: result } : value)
    } catch (caught) {
      setError(errorMessage(caught, 'Pengajuan tidak dapat dibatalkan.'))
    } finally {
      setSaving(false)
    }
  }

  return <>
    <Dashboard
      mine={mine}
      obrolan={obrolan}
      obrolanTotal={obrolanTotal}
      obrolanPage={obrolanPage}
      riwayat={riwayat}
      riwayatTotal={riwayatTotal}
      riwayatPage={riwayatPage}
      loading={loading}
      historyLoading={historyLoading}
      error={error}
      saving={saving}
      onRetry={() => void load()}
      onStart={() => router.push('/judul/rekomendasi')}
      onOpen={(query) => router.push(`/judul/rekomendasi?${query}`)}
      onCancel={() => setCancelDialogOpen(true)}
      onObrolanPage={(page) => void pindahObrolan(page)}
      onRiwayatPage={(page) => void pindahRiwayat(page)}
    />
    <ConfirmDialog
      open={cancelDialogOpen}
      title="Batalkan pengajuan judul?"
      description="Pengajuan ini akan dihentikan dan tidak lagi menunggu keputusan pembimbing."
      confirmLabel="Batalkan pengajuan"
      tone="danger"
      onCancel={() => setCancelDialogOpen(false)}
      onConfirm={() => void batalkan()}
    />
  </>
}

function Dashboard({ mine, obrolan, obrolanTotal, obrolanPage, riwayat, riwayatTotal, riwayatPage, loading, historyLoading, error, saving, onRetry, onStart, onOpen, onCancel, onObrolanPage, onRiwayatPage }: {
  mine: ThesisMine | null
  obrolan: ThesisChatSummary[]
  obrolanTotal: number
  obrolanPage: number
  riwayat: ThesisRecommendationSummary[]
  riwayatTotal: number
  riwayatPage: number
  loading: boolean
  historyLoading: boolean
  error: string
  saving: boolean
  onRetry: () => void
  onStart: () => void
  onOpen: (query: string) => void
  onCancel: () => void
  onObrolanPage: (page: number) => void
  onRiwayatPage: (page: number) => void
}) {
  const submission = mine?.pengajuan
  const activeSubmission = submission && submission.status !== 'dibatalkan' ? submission : null

  return <div className="page-content judul-page judul-dashboard">
    <header className="judul-heading">
      <div>
        <p className="eyebrow">RUANG RENCANA AKADEMIK</p>
        <h1>Rancang tugas akhirmu.</h1>
        <p>Mulai dari minat, temukan ide yang kuat, lalu ajukan saat siap.</p>
      </div>
      <button type="button" className="primary judul-start-button" onClick={onStart}><MessageSquareText aria-hidden="true" /> Mulai brainstorm <ArrowRight aria-hidden="true" /></button>
    </header>

    {error && <div className="judul-alert"><p>{error}</p><button type="button" className="outline-button" onClick={onRetry}>Coba lagi</button></div>}

    {loading ? <div className="workflow-card judul-loading-inline"><Loader2 className="spin" /> Memuat data judul tugas akhir...</div> : <>
      {activeSubmission ? <section className="workflow-card judul-submission-card">
        <div className="judul-section-kicker"><BookOpenCheck /> PENGAJUAN SAYA</div>
        <div className="judul-submission-head"><div>
          <span className={`judul-status ${statusTone(activeSubmission)}`}>{statusLabel(activeSubmission)}</span>
          <h2>{activeSubmission.judul}</h2>
          <span className="judul-theme-tag">{activeSubmission.tema}</span>
        </div>{activeSubmission.jumlah_revisi > 0 && <small>Revisi ke-{activeSubmission.jumlah_revisi}</small>}</div>
        {activeSubmission.catatan && <div className="judul-note"><b>Catatan pembimbing</b><p>{activeSubmission.catatan}</p></div>}
        <div className="judul-submission-footer"><p>Diajukan {tanggal(activeSubmission.diajukan_pada)}{activeSubmission.pembimbing ? ` · Pembimbing: ${activeSubmission.pembimbing.nama_lengkap}` : ''}</p>
          <div className="judul-action-row">{activeSubmission.tahap === 'perbaikan' && <button type="button" className="primary" onClick={onStart}>Perbaiki dan kirim ulang</button>}{activeSubmission.status === 'diajukan' && <button type="button" className="outline-button" disabled={saving} onClick={onCancel}>Batalkan pengajuan</button>}</div>
        </div>
      </section> : <section className="judul-idea-banner">
        <div className="judul-idea-mark"><FileText aria-hidden="true" /></div>
        <div className="judul-idea-copy"><span>LANGKAH PERTAMA</span><h2>Belum ada pengajuan judul</h2><p>Obrolkan minatmu dan kumpulkan beberapa kandidat sebelum memilih yang paling pas.</p></div>
        <button type="button" className="judul-idea-link" onClick={onStart}>Cari ide judul <ArrowRight /></button>
      </section>}

      <div className="judul-library-grid">
        <section className="workflow-card judul-library-card">
          <div className="judul-section-heading"><div className="judul-library-title"><span className="judul-library-icon"><MessageCircle /></span><div><h2>Obrolan ide</h2><p>Lanjutkan eksplorasi dan kandidat yang tersimpan.</p></div></div><span className="judul-count">{obrolanTotal}</span></div>
          {obrolan.length ? <div className="judul-history-list">{obrolan.map((item) => <div className="judul-history-item" key={item.id}><div className="judul-history-copy"><b>{item.topik}</b><small>{tanggal(item.diubah)} <span>·</span> {item.jumlah_kandidat} kandidat <span>·</span> {item.jumlah_disimpan} disimpan</small></div><button type="button" className="judul-open-button" aria-label={`Lanjutkan obrolan ${item.topik}`} onClick={() => onOpen(`obrolan=${item.id}`)}><ArrowRight /></button></div>)}</div> : <div className="judul-list-empty">Belum ada obrolan. Mulai brainstorm untuk menyimpan ide pertamamu.</div>}
          <Paginasi halaman={obrolanPage} total={obrolanTotal} ukuran={PAGE_SIZE} disabled={historyLoading} label="obrolan ide" onChange={onObrolanPage} />
        </section>

        {!!riwayatTotal && <section className="workflow-card judul-library-card judul-archive-card">
          <div className="judul-section-heading"><div className="judul-library-title"><span className="judul-library-icon archive"><Archive /></span><div><h2>Arsip rekomendasi</h2><p>Ide dari pencarian sebelumnya.</p></div></div><span className="judul-count">{riwayatTotal}</span></div>
          <div className="judul-history-list">{riwayat.map((item) => <div className="judul-history-item" key={item.id}><div className="judul-history-copy"><b>{item.topik}</b><small>{tanggal(item.dibuat)} <span>·</span> {item.jumlah_rekomendasi} rekomendasi</small></div><button type="button" className="judul-open-button" aria-label={`Buka rekomendasi ${item.topik}`} onClick={() => onOpen(`riwayat=${item.id}`)}><ArrowRight /></button></div>)}</div>
          <Paginasi halaman={riwayatPage} total={riwayatTotal} ukuran={PAGE_SIZE} disabled={historyLoading} label="arsip rekomendasi" onChange={onRiwayatPage} />
        </section>}
      </div>
    </>}
  </div>
}

function Paginasi({ halaman, total, ukuran, disabled, label, onChange }: { halaman: number; total: number; ukuran: number; disabled: boolean; label: string; onChange: (page: number) => void }) {
  const jumlahHalaman = Math.ceil(total / ukuran)
  if (jumlahHalaman < 2) return null

  const awal = Math.max(1, Math.min(halaman - 2, jumlahHalaman - 4))
  const akhir = Math.min(jumlahHalaman, awal + 4)
  const nomor = Array.from({ length: akhir - awal + 1 }, (_, index) => awal + index)

  return <nav className="judul-pagination" aria-label={`Pagination ${label}`}>
    <button type="button" className="judul-page-arrow" aria-label="Halaman sebelumnya" disabled={disabled || halaman === 1} onClick={() => onChange(halaman - 1)}><ChevronLeft /></button>
    <div className="judul-page-numbers">{nomor.map((page) => <button type="button" key={page} aria-current={page === halaman ? 'page' : undefined} disabled={disabled} onClick={() => onChange(page)}>{page}</button>)}</div>
    <button type="button" className="judul-page-arrow" aria-label="Halaman berikutnya" disabled={disabled || halaman === jumlahHalaman} onClick={() => onChange(halaman + 1)}><ChevronRight /></button>
    <span>Halaman {halaman} dari {jumlahHalaman}</span>
  </nav>
}
