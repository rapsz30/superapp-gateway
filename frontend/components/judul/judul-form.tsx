'use client'

import { useState } from 'react'
import { ArrowLeft, Check, Loader2, Send } from 'lucide-react'
import type { ThesisAdvisorOption, ThesisSubmissionInput as FormState, ThesisPerson } from '@/src/services/judul-service'

export function JudulForm({ form, themes, advisors, selectedAdvisorId, currentAdvisor, loading, saving, error, isRevision, onChange, onAdvisorChange, onSubmit, onBack }: {
  form: FormState
  themes: string[]
  advisors: ThesisAdvisorOption[]
  selectedAdvisorId: string
  currentAdvisor: ThesisPerson | null
  loading: boolean
  saving: boolean
  error: string
  isRevision: boolean
  onChange: <K extends keyof FormState>(key: K, value: FormState[K]) => void
  onAdvisorChange: (id: string) => void
  onSubmit: (event: React.FormEvent) => void
  onBack: () => void
}) {
  const [keywords, setKeywords] = useState(form.keywords.join(', '))
  const [references, setReferences] = useState(form.referensi.map((item) => `${item.sitasi} | ${item.link}`).join('\n'))
  const updateKeywords = (value: string) => { setKeywords(value); onChange('keywords', value.split(',').map((item) => item.trim()).filter(Boolean).slice(0, 10)) }
  const updateReferences = (value: string) => { setReferences(value); onChange('referensi', value.split('\n').map((line) => { const [sitasi, link] = line.split('|').map((item) => item.trim()); return { sitasi, link } }).filter((item) => item.sitasi && /^https?:\/\//i.test(item.link)).slice(0, 10)) }

  return <div className="page-content judul-application-page">
    <button type="button" className="judul-application-back" onClick={onBack}><ArrowLeft /> Kembali ke obrolan</button>
    <header className="judul-application-heading">
      <p className="eyebrow">{isRevision ? 'REVISI PENGAJUAN' : 'PENGAJUAN JUDUL'}</p>
      <h1>{isRevision ? 'Perbaiki judul tugas akhir' : 'Ajukan judul tugas akhir'}</h1>
      <p>{isRevision ? 'Perbarui isi judul sesuai catatan pembimbing.' : 'Pilih dosen pembimbing, lalu periksa kembali detail rencana penelitian Anda.'}</p>
    </header>

    <form onSubmit={onSubmit} className="judul-application-layout">
      <section className="judul-advisor-picker">
        <div className="judul-application-section-head"><span>01</span><div><h2>{isRevision ? 'Pembimbing saat ini' : 'Pilih dosen pembimbing'}</h2><p>{isRevision ? 'Revisi akan dikirim kembali kepada dosen yang meninjau pengajuan ini.' : 'Pilih salah satu dosen aktif di program studi Anda.'}</p></div></div>
        {isRevision ? <div className="judul-current-advisor"><span className="judul-advisor-avatar">{currentAdvisor?.nama_lengkap?.slice(0, 1) ?? 'D'}</span><div><strong>{currentAdvisor?.nama_lengkap ?? 'Pembimbing pengajuan'}</strong><small>Pembimbing tugas akhir</small></div><Check /></div> : loading ? <div className="judul-advisor-loading"><Loader2 className="spin" /> Memuat daftar dosen...</div> : advisors.length ? <div className="judul-advisor-options" role="radiogroup" aria-label="Pilih dosen pembimbing">{advisors.map((advisor) => <button key={advisor.id} type="button" role="radio" aria-checked={selectedAdvisorId === advisor.id} className={`judul-advisor-option ${selectedAdvisorId === advisor.id ? 'selected' : ''}`} onClick={() => onAdvisorChange(advisor.id)}><span className="judul-advisor-avatar">{advisor.nama_lengkap.slice(0, 1)}</span><span className="judul-advisor-option-copy"><strong>{advisor.nama_lengkap}</strong><small>Dosen pembimbing tugas akhir</small></span><span className="judul-advisor-radio" /></button>)}</div> : <p className="judul-advisor-empty">Belum ada dosen pembimbing aktif yang tersedia. Hubungi kaprodi untuk bantuan.</p>}
      </section>

      <section className="judul-application-details">
        <div className="judul-application-section-head"><span>02</span><div><h2>Detail rencana penelitian</h2><p>Pastikan informasi yang dikirim sudah tepat.</p></div></div>
        <div className="judul-form application-form">
          <label>Judul<input value={form.judul} minLength={10} maxLength={300} onChange={(event) => onChange('judul', event.target.value)} required /></label>
          <label>Tema<select value={form.tema} onChange={(event) => onChange('tema', event.target.value)} required><option value="">Pilih tema</option>{themes.map((theme) => <option key={theme} value={theme}>{theme}</option>)}</select></label>
          <label>Deskripsi<textarea value={form.deskripsi} minLength={20} maxLength={2000} rows={4} onChange={(event) => onChange('deskripsi', event.target.value)} required /></label>
          <label>Metodologi <span>(opsional)</span><textarea value={form.metodologi} maxLength={3000} rows={4} onChange={(event) => onChange('metodologi', event.target.value)} /></label>
          <label>Kata kunci <span>(pisahkan dengan koma)</span><input value={keywords} maxLength={600} onChange={(event) => updateKeywords(event.target.value)} /></label>
          <label>Referensi <span>(satu per baris: sitasi | https://...)</span><textarea value={references} rows={3} onChange={(event) => updateReferences(event.target.value)} /></label>
        </div>
        {error && <p className="form-error" role="alert">{error}</p>}
        <div className="judul-application-actions"><button type="button" className="outline-button" onClick={onBack}>Batal</button><button type="submit" className="primary" disabled={saving || loading || (!isRevision && !selectedAdvisorId)}>{saving ? <><Loader2 className="spin" /> Mengirim...</> : <><Send /> {isRevision ? 'Kirim revisi' : 'Kirim pengajuan'}</>}</button></div>
      </section>
    </form>
  </div>
}
