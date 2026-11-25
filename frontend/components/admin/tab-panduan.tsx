'use client'

import { useState } from 'react'
import { Modal } from 'antd'
import { adminService, type Panduan } from '@/src/services/admin-service'
import { Badge, Field, Kartu, Kosong, Notice, SelectProdi, konfirmasi, tanggal, useAksi, useLoad } from './ui'

const TONE = { aktif: 'hijau', draf: 'kuning', diarsipkan: 'abu' } as const

export function TabPanduan({ initialProdiId }: { initialProdiId?: string } = {}) {
  const [prodiId, setProdiId] = useState(initialProdiId ?? '')
  const daftar = useLoad(
    () => (prodiId ? adminService.daftarPanduan(prodiId) : Promise.resolve(null)),
    [prodiId],
  )
  const [judul, setJudul] = useState('')
  const [berlaku, setBerlaku] = useState('')
  const [berkas, setBerkas] = useState<File | null>(null)
  const [inputKey, setInputKey] = useState(0)
  const [unggahBuka, setUnggahBuka] = useState(false)
  const { sibuk, galat, ok, jalankan, setGalat, setOk } = useAksi()

  async function unggah(e: React.FormEvent) {
    e.preventDefault()
    if (!berkas || !prodiId) return
    const p = await jalankan(() => adminService.unggahPanduan(prodiId, judul.trim(), berkas, berlaku || undefined), 'Panduan diunggah sebagai draf. Aktifkan agar dipakai.')
    if (p) {
      setJudul('')
      setBerlaku('')
      setBerkas(null)
      setInputKey((n) => n + 1)
      setUnggahBuka(false)
      void daftar.reload()
    }
  }

  async function aktifkan(p: Panduan) {
    const aktifLama = daftar.data?.data.find((x) => x.status === 'aktif')
    const pesan = aktifLama
      ? `Aktifkan versi ${p.versi}? Versi ${aktifLama.versi} akan diarsipkan. Pengajuan yang sudah berjalan tetap memakai versi lamanya.`
      : `Aktifkan versi ${p.versi}?`
    if (!(await konfirmasi(pesan))) return
    const r = await jalankan(() => adminService.aktifkanPanduan(p.id), `Versi ${p.versi} aktif.`)
    if (r) void daftar.reload()
  }

  async function buka(p: Panduan) {
    const blob = await jalankan(() => adminService.unduhPanduan(p.id))
    if (!blob) return
    const url = URL.createObjectURL(blob)
    window.open(url, '_blank', 'noopener')
    setTimeout(() => URL.revokeObjectURL(url), 60_000)
  }

  return (
    <div className="adm-stack">
      <Kartu judul="Panduan akademik per program studi" aksi={prodiId ? <button className="adm-btn" onClick={() => setUnggahBuka(true)}>+ Unggah versi</button> : undefined}>
        <p className="adm-muted">
          Setiap prodi punya satu panduan <strong>aktif</strong>. Rekomendasi mata kuliah dan pemeriksaan KHS memakai panduan itu. Unggahan baru berstatus draf sampai diaktifkan;
          versi lama otomatis diarsipkan dan tidak pernah dihapus.
        </p>
        {!initialProdiId && <SelectProdi value={prodiId} onChange={setProdiId} />}
        {galat && <Notice tone="error" onClose={() => setGalat('')}>{galat}</Notice>}
        {ok && <Notice tone="ok" onClose={() => setOk('')}>{ok}</Notice>}
      </Kartu>

      {prodiId && (
        <>
          <Modal open={unggahBuka} title="Unggah panduan akademik" footer={null} width={720} onCancel={() => setUnggahBuka(false)}>
            <form className="adm-form" onSubmit={unggah}>
              <Field label="Judul"><input value={judul} onChange={(e) => setJudul(e.target.value)} required maxLength={300} placeholder="mis. Panduan Akademik Informatika 2024/2025" /></Field>
              <Field label="Berlaku mulai" hint="Opsional."><input type="date" value={berlaku} onChange={(e) => setBerlaku(e.target.value)} /></Field>
              <Field label="Berkas PDF" hint="Harus PDF berteks (bukan hasil pindai), maksimal 20 MB.">
                <input key={inputKey} type="file" accept="application/pdf,.pdf" onChange={(e) => setBerkas(e.target.files?.[0] ?? null)} required />
              </Field>
              <button className="adm-btn" disabled={!berkas || !judul.trim() || sibuk}>{sibuk ? 'Mengunggah…' : 'Unggah sebagai draf'}</button>
            </form>
          </Modal>

          <Kartu judul="Riwayat versi">
            {daftar.error && <Notice tone="error">{daftar.error}</Notice>}
            {daftar.loading && !daftar.data && <Kosong>Memuat…</Kosong>}
            {daftar.data && daftar.data.data.length === 0 && <Kosong>Belum ada panduan untuk prodi ini. Pengajuan KHS belum dapat dilakukan sebelum ada panduan aktif.</Kosong>}
            {daftar.data && daftar.data.data.length > 0 && (
              <div className="adm-scroll">
                <table className="adm-table">
                  <thead><tr><th>Versi</th><th>Judul</th><th>Status</th><th>Berlaku</th><th>Teks terbaca</th><th /></tr></thead>
                  <tbody>
                    {daftar.data.data.map((p) => (
                      <tr key={p.id}>
                        <td>v{p.versi}</td>
                        <td>{p.judul}<br /><small className="adm-muted">{p.berkas_nama}</small></td>
                        <td><Badge tone={TONE[p.status]}>{p.status}</Badge></td>
                        <td>{tanggal(p.berlaku_mulai)}</td>
                        <td>{p.teks_karakter != null ? `${p.teks_karakter.toLocaleString('id-ID')} karakter` : '—'}</td>
                        <td>
                          <div className="adm-row">
                            <button className="adm-link" disabled={sibuk} onClick={() => buka(p)}>Buka PDF</button>
                            {p.status !== 'aktif' && <button className="adm-link" disabled={sibuk} onClick={() => aktifkan(p)}>Aktifkan</button>}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Kartu>
        </>
      )}
    </div>
  )
}
