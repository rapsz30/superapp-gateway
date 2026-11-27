'use client'

import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { ArrowLeft, Brain, ChevronRight, FilePlus2, ListChecks, Loader2, MessageSquarePlus, Printer, RefreshCw, Send, Sparkles, Sprout, Star, X } from 'lucide-react'
import { useRouter, useSearchParams } from 'next/navigation'
import { TeksAI } from '@/components/judul/teks-ai'
import { errorMessage } from '@/src/lib/api'
import { judulService, type ThesisCandidate, type ThesisChat, type ThesisMine, type ThesisSubmissionInput as FormState } from '@/src/services/judul-service'

const emptyForm: FormState = { topik: '', judul: '', tema: '', deskripsi: '', metodologi: '', keywords: [], referensi: [] }

const topicSuggestions = [
  { title: 'Machine Learning', description: 'Saya tertarik pada klasifikasi dan prediksi data menggunakan machine learning.', prompt: 'Saya ingin mengeksplorasi ide tugas akhir tentang machine learning, terutama klasifikasi dan prediksi data.', icon: Sparkles },
  { title: 'Pertanian', description: 'Saya tertarik pada pemanfaatan teknologi untuk mengembangkan sektor pertanian.', prompt: 'Saya ingin mencari ide tugas akhir tentang teknologi di bidang pertanian.', icon: Sprout },
  { title: 'Psikologi', description: 'Saya tertarik memahami perilaku manusia melalui pendekatan teknologi dan penelitian.', prompt: 'Saya ingin mengeksplorasi ide tugas akhir yang berkaitan dengan psikologi dan teknologi.', icon: Brain },
]

const saranBahas = ['Apakah ini realistis untuk 4-6 bulan?', 'Datanya bisa diperoleh dari mana?', 'Tolong persempit judulnya.']

function toForm(k: ThesisCandidate, topik: string): FormState {
  return { topik, judul: k.judul, tema: k.tema, deskripsi: k.deskripsi, metodologi: k.metodologi, keywords: k.keywords, referensi: k.referensi }
}

/**
 * Brainstorm judul: ngobrol dulu, kumpulkan kandidat, bahas satu per satu. Membahas atau menyimpan kandidat
 * bukan memilih; memilih hanya terjadi saat mahasiswa mengajukan kepada pembimbing.
 */
export function BrainstormJudul() {
  const router = useRouter()
  const params = useSearchParams()
  const obrolanId = params.get('obrolan')
  const riwayatId = params.get('riwayat')
  const [mine, setMine] = useState<ThesisMine | null>(null)
  const [chat, setChat] = useState<ThesisChat | null>(null)
  const [fokus, setFokus] = useState<string | null>(null)
  const [input, setInput] = useState('')
  const [pending, setPending] = useState('')
  const [pendingUtas, setPendingUtas] = useState<string | null>(null)
  const [busy, setBusy] = useState<'' | 'pesan' | 'kandidat' | 'buka'>('')
  const [error, setError] = useState('')
  const [candidatePanelOpen, setCandidatePanelOpen] = useState(false)
  const [mobileView, setMobileView] = useState(false)
  const listRef = useRef<HTMLDivElement>(null)
  const composerRef = useRef<HTMLTextAreaElement>(null)
  const candidatePanelRef = useRef<HTMLElement>(null)
  const dibuka = useRef('')
  const alamat = useRef(obrolanId)
  alamat.current = obrolanId

  useEffect(() => {
    const media = window.matchMedia('(max-width: 700px)')
    const update = () => setMobileView(media.matches)
    update()
    media.addEventListener('change', update)
    return () => media.removeEventListener('change', update)
  }, [])

  useEffect(() => {
    if (!candidatePanelOpen || !mobileView) return
    const panel = candidatePanelRef.current
    if (!panel) return
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null
    const focusable = () => Array.from(panel.querySelectorAll<HTMLElement>('button:not(:disabled), a[href], [tabindex]:not([tabindex="-1"])'))
    focusable()[0]?.focus()
    function trapFocus(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setCandidatePanelOpen(false)
        return
      }
      if (event.key !== 'Tab') return
      const items = focusable()
      if (!items.length) return
      const first = items[0]
      const last = items[items.length - 1]
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }
    document.addEventListener('keydown', trapFocus)
    return () => {
      document.removeEventListener('keydown', trapFocus)
      if (previousFocus?.isConnected) previousFocus.focus()
    }
  }, [candidatePanelOpen, mobileView])

  useEffect(() => {
    judulService.saya()
      .then((saya) => setMine(saya))
      .catch((caught) => setError(errorMessage(caught, 'Data judul tugas akhir tidak dapat dimuat.')))
  }, [])

  useEffect(() => {
    if (!obrolanId && !riwayatId) { setChat(null); setFokus(null); setCandidatePanelOpen(false); dibuka.current = ''; return }
    if (obrolanId && chat?.id === obrolanId) return
    const kunci = obrolanId ?? `riwayat:${riwayatId}`
    if (dibuka.current === kunci) return
    dibuka.current = kunci
    setBusy('buka')
    setError('')
    setFokus(null)
    const ambil = obrolanId ? judulService.obrolan(obrolanId) : judulService.mulaiObrolan({ dari_rekomendasi: riwayatId! })
    ambil
      .then((hasil) => { setChat(hasil); setCandidatePanelOpen(hasil.kandidat.length > 0); if (!obrolanId) router.replace(`/judul/rekomendasi?obrolan=${hasil.id}`) })
      .catch((caught) => { dibuka.current = ''; setError(errorMessage(caught, 'Obrolan tidak dapat dibuka.')) })
      .finally(() => setBusy(''))
    // Hanya mengikuti perubahan alamat: obrolan yang baru dibuat sudah ada di state sebelum alamatnya berganti.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [obrolanId, riwayatId])

  useEffect(() => {
    const list = listRef.current
    if (list) list.scrollTop = list.scrollHeight
  }, [chat?.id, chat?.pesan.length, fokus, pending, busy])

  useLayoutEffect(() => {
    const textarea = composerRef.current
    if (!textarea) return
    textarea.style.height = 'auto'
    textarea.style.height = `${Math.min(textarea.scrollHeight + 2, 160)}px` // +2 untuk garis tepi
  }, [input, chat?.id])

  /** Jalankan satu aksi obrolan; galat ditampilkan dan teks yang belum terkirim dikembalikan. */
  async function jalankan(jenis: 'pesan' | 'kandidat', aksi: () => Promise<ThesisChat>, teks = '') {
    if (busy) return
    setBusy(jenis)
    setError('')
    setPending(teks)
    setPendingUtas(fokus)
    if (teks) setInput('')
    const asal = alamat.current
    try {
      const hasil = await aksi()
      if (alamat.current !== asal) return // mahasiswa sudah pindah ke obrolan lain
      setChat(hasil)
      if (jenis === 'kandidat' && hasil.kandidat.length > 0) setCandidatePanelOpen(true)
      if (hasil.id !== obrolanId) router.replace(`/judul/rekomendasi?obrolan=${hasil.id}`)
    } catch (caught) {
      if (teks) setInput((sekarang) => sekarang || teks)
      setError(errorMessage(caught, 'AI belum dapat membalas. Coba lagi.'))
    } finally {
      setPending('')
      setBusy('')
    }
  }

  function kirim(teks: string) {
    if (busy) return
    const isi = teks.trim()
    if (isi.length < 3) { setError('Tuliskan minimal 3 karakter.'); return }
    void jalankan('pesan', () => chat ? judulService.kirimPesan(chat.id, isi, fokus) : judulService.mulaiObrolan({ pesan: isi }), isi)
  }

  async function ubahKandidat(aksi: () => Promise<ThesisChat>) {
    setError('')
    try {
      setChat(await aksi())
    } catch (caught) {
      setError(errorMessage(caught, 'Perubahan belum tersimpan.'))
    }
  }

  const pengajuan = mine?.pengajuan
  const revisi = pengajuan?.tahap === 'perbaikan'
  const menunggu = pengajuan?.status === 'diajukan' && !revisi

  function bukaForm(isi: FormState, isRevision = false, pengajuanId: string | null = null) {
    setError('')
    try {
      sessionStorage.setItem('judul-form-pengajuan', JSON.stringify({ form: isi, isRevision, pengajuanId, pembimbingId: mine?.pembimbing?.id ?? null }))
    } catch {
      setError('Form pengajuan belum dapat disiapkan. Coba lagi.')
      return
    }
    router.push('/judul/pengajuan')
  }

  const banner = (revisi || menunggu) && pengajuan && <div className="brainstorm-banner">
    {revisi
      ? <><p><b>Pembimbing meminta revisi.</b> {pengajuan.catatan}</p><button type="button" className="outline-button" onClick={() => bukaForm({ topik: pengajuan.topik, judul: pengajuan.judul, tema: pengajuan.tema, deskripsi: pengajuan.deskripsi, metodologi: pengajuan.metodologi, keywords: pengajuan.keywords, referensi: pengajuan.referensi }, true, pengajuan.id)}>Perbaiki judul yang diajukan</button></>
      : <p>Judul Anda sedang menunggu pembimbing. Brainstorm tetap bisa; pengajuan baru dapat dikirim setelah ada keputusan atau pengajuan dibatalkan.</p>}
  </div>

  if (!chat && (obrolanId || riwayatId)) {
    if (error) return <div className="page-content brainstorm"><Link className="brainstorm-back-link" href="/judul/beranda"><ArrowLeft aria-hidden="true" /> Kembali ke beranda judul</Link><p className="form-error" role="alert">{error}</p><button type="button" className="outline-button" onClick={() => router.push('/judul/rekomendasi')}>Mulai obrolan baru</button></div>
    return <RangkaMemuat />
  }

  // Pesan pertama: langsung pindah ke tampilan percakapan sambil menunggu balasan.
  const tampil: ThesisChat | null = chat ?? (busy === 'pesan' && pending ? { id: '', topik: pending, pesan: [], kandidat: [] } : null)

  if (!tampil) {
    return <div className="page-content thesis-chat-page">
      <Link className="brainstorm-back-link" href="/judul/beranda"><ArrowLeft aria-hidden="true" /> Kembali ke beranda judul</Link>
      {banner}
      <div className="thesis-chat-header"><img className="thesis-chat-illustration" src="/images/thesis-thinking.png" alt="" width={1536} height={1024} /><h1>Topik apa yang Anda minati?</h1></div>
      <div className="chat-suggestions">{topicSuggestions.map(({ title, description, prompt, icon: Icon }) => <button type="button" className="chat-suggestion" key={title} onClick={() => setInput(prompt)}><span className="chat-suggestion-icon"><Icon /></span><strong>{title}</strong><p>{description}</p></button>)}</div>
      <h2 className="thesis-chat-alt" id="thesis-custom-idea">Punya ide lain?</h2>
      <form className="chat-panel chat-composer" onSubmit={(event) => { event.preventDefault(); kirim(input) }} aria-busy={!!busy}>
        <textarea ref={composerRef} value={input} onChange={(event) => { setInput(event.target.value); setError('') }} maxLength={1000} placeholder="Ceritakan ide, masalah, atau bidang yang ingin Anda jajaki. Belum yakin juga tidak apa-apa." rows={3} aria-labelledby="thesis-custom-idea" disabled={!!busy} />
        {error && <p className="form-error" role="alert">{error}</p>}
        <div className="chat-composer-footer"><button type="submit" className="primary chat-send" disabled={!!busy}>Mulai brainstorm</button></div>
      </form>
      <button type="button" className="outline-button judul-own-button" onClick={() => bukaForm(emptyForm)}>Sudah punya judul? Ajukan sendiri</button>
    </div>
  }

  const dibahas = tampil.kandidat.find((k) => k.id === fokus) ?? null
  const utas = tampil.pesan.filter((p) => p.kandidat_id === (dibahas?.id ?? null))
  const terakhir = utas[utas.length - 1]
  const chips = terakhir?.peran === 'asisten' && terakhir.saran.length ? terakhir.saran : dibahas && !utas.length ? saranBahas : []
  const menunggu_di_sini = busy === 'pesan' && pendingUtas === (dibahas?.id ?? null)
  const urut = [...tampil.kandidat].sort((a, b) => Number(b.disimpan) - Number(a.disimpan))

  const aksi = (k: ThesisCandidate, bahas: boolean) => <div className="kandidat-aksi">
    {bahas && <button type="button" className="outline-button" onClick={() => { setFokus(k.id); setError(''); setInput(''); if (mobileView) setCandidatePanelOpen(false) }}>Bahas</button>}
    <button type="button" className={`outline-button ${k.disimpan ? 'tersimpan' : ''}`} aria-pressed={k.disimpan} onClick={() => void ubahKandidat(() => judulService.simpanKandidat(tampil.id, k.id, !k.disimpan))}><Star />{k.disimpan ? 'Disimpan' : 'Simpan'}</button>
    <button type="button" className="outline-button" disabled={menunggu} title={menunggu ? 'Masih ada judul yang menunggu pembimbing' : undefined} onClick={() => { if (mobileView) setCandidatePanelOpen(false); bukaForm(toForm(k, tampil.topik)) }}>Ajukan</button>
  </div>

  return <div className="page-content brainstorm">
    {banner}
      <div className={`brainstorm-grid ${candidatePanelOpen && tampil.kandidat.length > 0 ? 'has-candidates' : ''}`}>
      <section className="brainstorm-chat" aria-label="Percakapan">
        <header className="brainstorm-head">
          {dibahas
            ? <><div><Link className="brainstorm-back-link" href="/judul/beranda"><ArrowLeft aria-hidden="true" /> Kembali ke beranda judul</Link><p>Membahas kandidat · belum diajukan</p><h1>{dibahas.judul}</h1></div><button type="button" className="outline-button" onClick={() => { setFokus(null); setError(''); setInput('') }}><ArrowLeft /> Brainstorm</button></>
            : <><div><Link className="brainstorm-back-link" href="/judul/beranda"><ArrowLeft aria-hidden="true" /> Kembali ke beranda judul</Link><h1>Brainstorm ide judul</h1><p>Ceritakan dulu arahnya. Judul dibuat saat Anda memintanya.</p></div><div className="brainstorm-head-actions">{tampil.kandidat.length > 0 && <button type="button" className={`candidate-panel-toggle ${candidatePanelOpen ? 'active' : ''}`} aria-expanded={candidatePanelOpen} aria-controls="candidate-list-panel" onClick={() => setCandidatePanelOpen((open) => !open)}><ListChecks /> Kandidat judul ({tampil.kandidat.length})</button>}<button type="button" className="outline-button" disabled={!!busy} onClick={() => { setInput(''); setError(''); setCandidatePanelOpen(false); router.push('/judul/rekomendasi') }}><MessageSquarePlus /> Obrolan baru</button></div></>}
        </header>
        <div className="brainstorm-messages" ref={listRef} aria-live="polite">
          {!utas.length && !menunggu_di_sini && busy !== 'kandidat' && <p className="brainstorm-intro">{dibahas ? 'Tanyakan apa saja tentang kandidat ini: kelayakan, data, tingkat kesulitan, atau minta dipersempit. Membahas tidak berarti memilih.' : 'Mulai dengan menceritakan minat Anda.'}</p>}
          {utas.map((p) => <div key={p.id} style={{ display: 'contents' }}>
            <div className={`chat-bubble ${p.peran}`}>{p.peran === 'asisten' ? <TeksAI teks={p.isi} /> : p.isi}</div>
            {p.usulan && <div className="chat-usulan"><small>Usulan perbaikan</small><h3>{p.usulan.judul}</h3><span className="judul-theme-tag">{p.usulan.tema}</span><p>{p.usulan.deskripsi}</p>
              {p.versi_id
                ? <button type="button" className="outline-button" onClick={() => setFokus(p.versi_id)}>Tersimpan · bahas versi ini</button>
                : <button type="button" className="primary small" onClick={() => void ubahKandidat(() => judulService.simpanVersi(tampil.id, p.id))}>Simpan sebagai versi baru</button>}
            </div>}
          </div>)}
          {menunggu_di_sini && <><div className="chat-bubble mahasiswa">{pending}</div>
            <div className="chat-bubble asisten mengetik" role="status"><span /><span /><span /><em>AI sedang menulis</em></div></>}
          {busy === 'kandidat' && !dibahas && <div className="chat-bubble asisten menunggu" role="status"><Loader2 className="spin" size={15} /> Menyusun tiga kandidat judul dan mencari referensi, bisa sampai 40 detik...</div>}
          {!dibahas && tampil.kandidat.length > 0 && <button type="button" className="chat-candidate-link" onClick={() => setCandidatePanelOpen(true)}>Lihat {tampil.kandidat.length} kandidat judul <ChevronRight /></button>}
        </div>
        <div className="brainstorm-foot">
          {chips.length > 0 && !busy && tampil.id && <div className="chat-chips">{chips.map((s) => <button type="button" key={s} onClick={() => kirim(s)}>{s}</button>)}</div>}
          {error && <p className="form-error" role="alert">{error}</p>}
          <form className="brainstorm-input" onSubmit={(event) => { event.preventDefault(); kirim(input) }}>
            <textarea ref={composerRef} value={input} rows={1} maxLength={1000} disabled={!!busy} aria-label="Pesan" placeholder={dibahas ? 'Tanyakan tentang kandidat ini...' : 'Balas atau tambahkan cerita...'}
              onChange={(event) => { setInput(event.target.value); setError('') }}
              onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); kirim(input) } }} />
            <div className="brainstorm-send-actions">
              <button type="submit" className="primary" disabled={!!busy || !input.trim()}>{busy === 'pesan' ? <Loader2 className="spin" size={15} /> : <Send size={15} />} Kirim</button>
              {!dibahas && <button type="button" className="outline-button candidate-generate-button" disabled={!!busy || !tampil.id} onClick={() => void jalankan('kandidat', () => judulService.buatKandidat(tampil.id))}>{busy === 'kandidat' ? <Loader2 className="spin" size={15} /> : tampil.kandidat.length ? <RefreshCw /> : <FilePlus2 />} {busy === 'kandidat' ? 'Menyusun...' : tampil.kandidat.length ? 'Buatkan judul lagi' : 'Buatkan judul'}</button>}
            </div>
          </form>
        </div>
      </section>
      {candidatePanelOpen && tampil.kandidat.length > 0 && <button type="button" className="candidate-panel-backdrop" aria-label="Tutup panel kandidat" tabIndex={-1} onClick={() => setCandidatePanelOpen(false)} />}
      {candidatePanelOpen && tampil.kandidat.length > 0 && <aside ref={candidatePanelRef} id="candidate-list-panel" className="brainstorm-aside" role={mobileView ? 'dialog' : 'complementary'} aria-modal={mobileView || undefined} aria-labelledby="candidate-list-title">
        <div className="brainstorm-aside-head"><div><h2 id="candidate-list-title">Kandidat judul ({tampil.kandidat.length})</h2><p>Hasil rekomendasi berdasarkan diskusi</p></div><button type="button" className="candidate-panel-close" aria-label="Tutup panel kandidat" onClick={() => setCandidatePanelOpen(false)}><X /></button></div>
        {urut.map((k, index) => <KartuKandidat key={k.id} kandidat={k} aktif={k.id === fokus} nomor={index + 1}>{aksi(k, k.id !== fokus)}</KartuKandidat>)}
        <div className="brainstorm-aside-footer"><button type="button" className="outline-button" onClick={() => window.print()}><Printer /> Cetak kandidat</button></div>
      </aside>}
    </div>
  </div>
}

function RangkaMemuat() {
  return <div className="page-content brainstorm" role="status" aria-label="Membuka obrolan">
    <div className="brainstorm-grid">
      <section className="brainstorm-chat"><div className="brainstorm-head"><div><Link className="brainstorm-back-link" href="/judul/beranda"><ArrowLeft aria-hidden="true" /> Kembali ke beranda judul</Link><h1>Membuka obrolan...</h1></div></div><div className="brainstorm-messages"><div className="rangka-bubble kanan" /><div className="rangka-bubble" /><div className="rangka-bubble kanan" /></div></section>
    </div>
  </div>
}

function KartuKandidat({ kandidat: k, aktif, nomor, children }: { kandidat: ThesisCandidate; aktif: boolean; nomor: number; children: React.ReactNode }) {
  const [terbuka, setTerbuka] = useState(false)
  return <article className={`kandidat ${aktif ? 'aktif' : ''}`}>
    <div className="kandidat-label"><span className="kandidat-overline">KANDIDAT {nomor}</span><span className="judul-theme-tag">{k.tema}</span>{k.versi_dari && <span className="judul-theme-tag versi">Versi perbaikan</span>}</div>
    <h3>{k.judul}</h3>
    <button type="button" className="kandidat-buka" aria-expanded={terbuka} onClick={() => setTerbuka((v) => !v)}>{terbuka ? 'Sembunyikan detail' : 'Lihat detail'}</button>
    <div className={`kandidat-detail ${terbuka ? 'terbuka' : ''}`}>
      <p>{k.deskripsi}</p>
      {k.metodologi && <><b>Metodologi</b><TeksAI teks={k.metodologi} /></>}
      {k.referensi.length > 0 && <><b>Referensi</b>{k.referensi.map((r, i) => <a href={r.link} target="_blank" rel="noopener noreferrer" key={`${r.link}-${i}`}>{r.sitasi}</a>)}</>}
    </div>
    {children}
  </article>
}
