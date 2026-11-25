'use client'

import { useState } from 'react'
import { Modal } from 'antd'
import { adminService, type Orang } from '@/src/services/admin-service'
import { Badge, Field, Kartu, Kosong, Notice, OrangPicker, Pager, SandiSementara, konfirmasi, tanggal, useAksi, useLoad, useOrang } from './ui'

const UKURAN = 20

export function TabBimbingan({ prodiId }: { prodiId?: string } = {}) {
  const [aktif, setAktif] = useState<'ya' | 'tidak' | 'semua'>('ya')
  const [dosenFilter, setDosenFilter] = useState<Orang | null>(null)
  const [halaman, setHalaman] = useState(1)
  const [baru, setBaru] = useState(false)
  const [pindah, setPindah] = useState(false)

  const daftar = useLoad(
    async () => {
      const hasil = await adminService.daftarBimbingan({
        dosen_id: dosenFilter?.id,
        aktif: aktif === 'semua' ? undefined : aktif === 'ya',
        halaman,
        ukuran: UKURAN,
      })
      if (!prodiId) return hasil
      const anggota = await adminService.daftarKeanggotaan({ prodi_id: prodiId, aktif: true, ukuran: 200 })
      const mahasiswa = new Set(anggota.data.map((item) => item.orang_id))
      return { data: hasil.data.filter((item) => mahasiswa.has(item.mahasiswa_id)), total: hasil.data.filter((item) => mahasiswa.has(item.mahasiswa_id)).length }
    },
    [prodiId, aktif, dosenFilter?.id, halaman],
  )
  const nama = useOrang((daftar.data?.data ?? []).flatMap((b) => [b.dosen_id, b.mahasiswa_id]))
  const { sibuk, galat, ok, jalankan, setGalat, setOk } = useAksi()

  async function akhiri(id: string) {
    if (!(await konfirmasi('Akhiri bimbingan ini? Pengajuan yang sedang berjalan akan tetap dengan DPA saat ini sampai ada DPA baru.'))) return
    const r = await jalankan(() => adminService.akhiriBimbingan(id), 'Bimbingan diakhiri.')
    if (r) void daftar.reload()
  }

  return (
    <div className="adm-stack">
      <Kartu
        judul="Dosen pembimbing akademik (DPA)"
        aksi={
          <div className="adm-row">
            <button className="adm-btn adm-ghost" onClick={() => { setPindah(!pindah); setBaru(false) }}>Alihkan massal</button>
            <button className="adm-btn" onClick={() => { setBaru(!baru); setPindah(false) }}>+ Bimbingan</button>
          </div>
        }
      >
        <p className="adm-muted">
          Satu mahasiswa hanya punya satu DPA aktif. Dosen harus punya penugasan <code>dosen_pa</code> yang mencakup prodi mahasiswa (lihat tab Penugasan),
          dan DPA harus sudah punya akun agar dapat menerima pengajuan.
        </p>
        {galat && <Notice tone="error" onClose={() => setGalat('')}>{galat}</Notice>}
        {ok && <Notice tone="ok" onClose={() => setOk('')}>{ok}</Notice>}
        {baru && <Modal open title="Tambah bimbingan DPA" footer={null} onCancel={() => setBaru(false)}><FormBimbingan onSelesai={() => { setBaru(false); setOk('Bimbingan dibuat.'); void daftar.reload() }} /></Modal>}
        {pindah && <Modal open title="Alihkan bimbingan massal" footer={null} width={720} onCancel={() => setPindah(false)}><FormPindah onSelesai={(n) => { setPindah(false); setOk(`${n} mahasiswa dialihkan.`); void daftar.reload() }} /></Modal>}

        <div className="adm-filter">
          <OrangPicker label="Dosen" peran="dosen_pa" value={dosenFilter} onChange={(o) => { setHalaman(1); setDosenFilter(o) }} />
          <Field label="Status">
            <select value={aktif} onChange={(e) => { setHalaman(1); setAktif(e.target.value as typeof aktif) }}>
              <option value="ya">Aktif</option>
              <option value="tidak">Sudah berakhir</option>
              <option value="semua">Semua</option>
            </select>
          </Field>
        </div>

        {daftar.error && <Notice tone="error">{daftar.error}</Notice>}
        {daftar.loading && !daftar.data && <Kosong>Memuat…</Kosong>}
        {daftar.data && daftar.data.data.length === 0 && <Kosong>Tidak ada bimbingan.</Kosong>}
        {daftar.data && daftar.data.data.length > 0 && (
          <div className="adm-scroll">
            <table className="adm-table">
              <thead><tr><th>Mahasiswa</th><th>DPA</th><th>Mulai</th><th>Selesai</th><th /></tr></thead>
              <tbody>
                {daftar.data.data.map((b) => (
                  <tr key={b.id}>
                    <td>{nama(b.mahasiswa_id)}</td>
                    <td>{nama(b.dosen_id)}</td>
                    <td>{tanggal(b.mulai)}</td>
                    <td>{b.selesai ? tanggal(b.selesai) : <Badge tone="hijau">aktif</Badge>}</td>
                    <td>{!b.selesai && <button className="adm-link" disabled={sibuk} onClick={() => akhiri(b.id)}>Akhiri</button>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {daftar.data && <Pager halaman={halaman} ukuran={UKURAN} total={daftar.data.total} onChange={setHalaman} />}
      </Kartu>
    </div>
  )
}

export function FormMahasiswa({ prodiId, onSelesai }: { prodiId: string; onSelesai: (rahasia: { email: string; sandi: string } | null) => void }) {
  const [nama, setNama] = useState('')
  const [nim, setNim] = useState('')
  const [emailKontak, setEmailKontak] = useState('')
  const [emailAkun, setEmailAkun] = useState('')
  const [angkatan, setAngkatan] = useState('')
  const { sibuk, galat, jalankan } = useAksi()

  async function kirim(e: React.FormEvent) {
    e.preventDefault()
    const mahasiswa = await jalankan(async () => {
      const orang = await adminService.buatOrang({ nama_lengkap: nama.trim(), nim: nim.trim(), email_kontak: emailKontak.trim() || null })
      await adminService.buatKeanggotaan({ orang_id: orang.id, prodi_id: prodiId, angkatan: angkatan ? Number(angkatan) : null })
      if (emailAkun.trim()) {
        const akun = await adminService.buatAkun({ orang_id: orang.id, email: emailAkun.trim(), sandi: null })
        return { orang, akun }
      }
      return { orang, akun: null }
    })
    if (mahasiswa) onSelesai(mahasiswa.akun?.sandi_sementara ? { email: mahasiswa.akun.email, sandi: mahasiswa.akun.sandi_sementara } : null)
  }

  return <form className="adm-form" onSubmit={kirim}>
    {galat && <Notice tone="error">{galat}</Notice>}
    <Field label="Nama lengkap"><input value={nama} onChange={(e) => setNama(e.target.value)} required maxLength={200} /></Field>
    <Field label="NIM"><input value={nim} onChange={(e) => setNim(e.target.value)} required maxLength={32} /></Field>
    <Field label="Email akun" hint="Opsional. Jika diisi, sandi sementara akan ditampilkan setelah berhasil."><input type="email" value={emailAkun} onChange={(e) => setEmailAkun(e.target.value)} /></Field>
    <Field label="Email kontak" hint="Opsional bila berbeda dengan email akun."><input type="email" value={emailKontak} onChange={(e) => setEmailKontak(e.target.value)} /></Field>
    <Field label="Angkatan"><input type="number" min={1990} max={2100} value={angkatan} onChange={(e) => setAngkatan(e.target.value)} placeholder="mis. 2026" /></Field>
    <button className="adm-btn" disabled={sibuk}>{sibuk ? 'Menyimpan…' : 'Buat mahasiswa'}</button>
  </form>
}

function FormBimbingan({ onSelesai }: { onSelesai: () => void }) {
  const [mhs, setMhs] = useState<Orang | null>(null)
  const [dosen, setDosen] = useState<Orang | null>(null)
  const { sibuk, galat, jalankan } = useAksi()

  async function kirim(e: React.FormEvent) {
    e.preventDefault()
    if (!mhs || !dosen) return
    const r = await jalankan(() => adminService.buatBimbingan({ dosen_id: dosen.id, mahasiswa_id: mhs.id }))
    if (r) onSelesai()
  }

  return (
    <form className="adm-form adm-boxed" onSubmit={kirim}>
      <h3>Bimbingan baru</h3>
      {galat && <Notice tone="error">{galat}</Notice>}
      <OrangPicker label="Mahasiswa" peran="mahasiswa" value={mhs} onChange={setMhs} />
      <OrangPicker label="Dosen PA" peran="dosen_pa" value={dosen} onChange={setDosen} />
      <button className="adm-btn" disabled={!mhs || !dosen || sibuk}>{sibuk ? 'Menyimpan…' : 'Simpan'}</button>
    </form>
  )
}

function FormPindah({ onSelesai }: { onSelesai: (n: number) => void }) {
  const [asal, setAsal] = useState<Orang | null>(null)
  const [tujuan, setTujuan] = useState<Orang | null>(null)
  const { sibuk, galat, jalankan } = useAksi()

  async function kirim(e: React.FormEvent) {
    e.preventDefault()
    if (!asal || !tujuan) return
    if (!(await konfirmasi(`Alihkan SEMUA mahasiswa aktif ${asal.nama_lengkap} ke ${tujuan.nama_lengkap}? Pengajuan yang berjalan ikut dialihkan.`))) return
    const r = await jalankan(() => adminService.pindahkanBimbingan({ dosen_asal_id: asal.id, dosen_tujuan_id: tujuan.id }))
    if (r) onSelesai(r.dialihkan)
  }

  return (
    <form className="adm-form adm-boxed" onSubmit={kirim}>
      <h3>Alihkan semua mahasiswa dari satu DPA</h3>
      <p className="adm-muted">Untuk dosen yang berhenti atau cuti. Dilakukan dalam satu transaksi: bila ada yang gagal, tidak ada yang berubah.</p>
      {galat && <Notice tone="error">{galat}</Notice>}
      <OrangPicker label="Dosen asal" peran="dosen_pa" value={asal} onChange={setAsal} />
      <OrangPicker label="Dosen tujuan" peran="dosen_pa" value={tujuan} onChange={setTujuan} />
      <button className="adm-btn" disabled={!asal || !tujuan || sibuk}>{sibuk ? 'Memproses…' : 'Alihkan'}</button>
    </form>
  )
}
