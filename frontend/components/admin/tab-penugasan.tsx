'use client'

import { useMemo, useState } from 'react'
import { Modal } from 'antd'
import { adminService, type Orang, type Peran, type UnitTipe } from '@/src/services/admin-service'
import { Badge, Field, Kartu, Kosong, Notice, OrangPicker, Pager, namaUnit, tanggal, useAksi, useKonfirmasi, useLoad, useOrang, useStruktur } from './ui'

const PERAN: Peran[] = ['superadmin', 'dekan', 'kajur', 'kaprodi', 'dosen_pa']
const UNIT_SAH: Record<Peran, UnitTipe[]> = {
  superadmin: ['global'],
  dekan: ['fakultas'],
  kajur: ['jurusan'],
  kaprodi: ['prodi'],
  dosen_pa: ['prodi', 'jurusan'],
}
const KETERANGAN: Record<Peran, string> = {
  superadmin: 'Mengelola seluruh sistem.',
  dekan: 'Satu dekan aktif per fakultas.',
  kajur: 'Satu kajur aktif per jurusan.',
  kaprodi: 'Satu kaprodi aktif per prodi. Dapat mengelola panduan dan dosen PA di prodinya.',
  dosen_pa: 'Dosen pembimbing akademik. Dapat ditugaskan di beberapa prodi atau satu jurusan.',
}
const UKURAN = 20

export function TabPenugasan({ prodiId }: { prodiId?: string } = {}) {
  const { isSuper, pohon, unit } = useStruktur()
  const [peranFilter, setPeranFilter] = useState('')
  const [aktif, setAktif] = useState<'ya' | 'tidak' | 'semua'>('ya')
  const [halaman, setHalaman] = useState(1)
  const [baru, setBaru] = useState(false)
  const [dosenBaru, setDosenBaru] = useState(false)
  const konfirmasi = useKonfirmasi()

  const daftar = useLoad(
      () => adminService.daftarPenugasan({ unit_id: prodiId, peran: peranFilter || undefined, aktif: aktif === 'semua' ? undefined : aktif === 'ya', halaman, ukuran: UKURAN }),
    [prodiId, peranFilter, aktif, halaman],
  )
  const namaOrang = useOrang((daftar.data?.data ?? []).map((p) => p.orang_id))
  const { sibuk, galat, ok, jalankan, setGalat, setOk } = useAksi()

  async function akhiri(id: string) {
    if (!(await konfirmasi('Akhiri penugasan ini mulai hari ini?'))) return
    const r = await jalankan(() => adminService.akhiriPenugasan(id), 'Penugasan diakhiri.')
    if (r) void daftar.reload()
  }

  return (
    <div className="adm-stack">
      <Kartu
        judul="Penugasan jabatan"
        aksi={
          <div className="adm-row">
            {prodiId && isSuper && <button className="adm-btn adm-ghost" onClick={() => { setDosenBaru(true); setBaru(false) }}>+ Akun dosen</button>}
            <button className="adm-btn" onClick={() => { setBaru(!baru); setDosenBaru(false) }}>{baru ? 'Tutup' : prodiId ? '+ Dosen PA' : '+ Penugasan'}</button>
          </div>
        }
      >
        {isSuper && prodiId && <Notice>Admin dapat menambahkan Dosen PA ke Prodi ini. Dosen yang sama boleh ditugaskan di Prodi lain tanpa mengakhiri penugasan sebelumnya.</Notice>}
        {!isSuper && <Notice>Kaprodi hanya dapat menugaskan dosen PA pada prodinya sendiri. Satu dosen PA dapat ditugaskan di beberapa prodi.</Notice>}
        {galat && <Notice tone="error" onClose={() => setGalat('')}>{galat}</Notice>}
        {ok && <Notice tone="ok" onClose={() => setOk('')}>{ok}</Notice>}
        {baru && <Modal open title={prodiId ? 'Tambah Dosen PA ke Prodi' : 'Tambah penugasan'} footer={null} width={720} onCancel={() => setBaru(false)}><FormPenugasan pohon={pohon} prodiId={prodiId} onSelesai={() => { setBaru(false); setOk('Penugasan dibuat.'); void daftar.reload() }} /></Modal>}
        {dosenBaru && prodiId && <Modal open title="Tambah akun dosen ke Prodi" footer={null} width={720} onCancel={() => setDosenBaru(false)}><FormDosenProdi prodiId={prodiId} onSelesai={() => { setDosenBaru(false); setOk('Akun dosen dan penugasan Prodi berhasil dibuat.'); void daftar.reload() }} /></Modal>}

        <div className="adm-filter">
          {!prodiId && <Field label="Peran">
            <select value={peranFilter} onChange={(e) => { setHalaman(1); setPeranFilter(e.target.value) }}>
              <option value="">Semua</option>
              {PERAN.map((p) => <option key={p}>{p}</option>)}
            </select>
          </Field>}
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
        {daftar.data && daftar.data.data.length === 0 && <Kosong>Tidak ada penugasan.</Kosong>}
        {daftar.data && daftar.data.data.length > 0 && (
          <div className="adm-scroll">
            <table className="adm-table">
              <thead><tr><th>Orang</th><th>Peran</th><th>Unit</th><th>Mulai</th><th>Selesai</th><th /></tr></thead>
              <tbody>
                {daftar.data.data.map((p) => {
                  const berakhir = !!p.selesai && p.selesai <= new Date().toISOString().slice(0, 10)
                  return (
                    <tr key={p.id}>
                      <td>{namaOrang(p.orang_id)}</td>
                      <td><Badge tone="biru">{p.peran}</Badge></td>
                      <td>{p.unit_tipe === 'global' ? 'Seluruh sistem' : `${p.unit_tipe}: ${namaUnit(unit, p.unit_id)}`}</td>
                      <td>{tanggal(p.mulai)}</td>
                      <td>{tanggal(p.selesai)}</td>
                      <td>{!berakhir && <button className="adm-link" disabled={sibuk} onClick={() => akhiri(p.id)}>Akhiri</button>}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
        {daftar.data && <Pager halaman={halaman} ukuran={UKURAN} total={daftar.data.total} onChange={setHalaman} />}
      </Kartu>
    </div>
  )
}

function FormDosenProdi({ prodiId, onSelesai }: { prodiId: string; onSelesai: (hasil: import('@/src/services/admin-service').DosenProdiResult) => void }) {
  const [nama, setNama] = useState('')
  const [nidn, setNidn] = useState('')
  const [emailKontak, setEmailKontak] = useState('')
  const [email, setEmail] = useState('')
  const [sandi, setSandi] = useState('')
  const { sibuk, galat, jalankan } = useAksi()

  async function kirim(e: React.FormEvent) {
    e.preventDefault()
    const hasil = await jalankan(() => adminService.buatDosenProdi(prodiId, {
      nama_lengkap: nama.trim(),
      nidn: nidn.trim() || null,
      email_kontak: emailKontak.trim() || null,
      email: email.trim(),
      sandi,
    }))
    if (hasil) onSelesai(hasil)
  }

  return (
    <form className="adm-form adm-boxed" onSubmit={kirim}>
      <h3>Data akun dosen</h3>
      <p className="adm-muted">Akun akan langsung diberi peran Dosen PA pada Prodi ini. Sandi diisi langsung oleh admin.</p>
      {galat && <Notice tone="error">{galat}</Notice>}
      <Field label="Nama lengkap"><input value={nama} onChange={(e) => setNama(e.target.value)} required maxLength={200} /></Field>
      <Field label="NIDN"><input value={nidn} onChange={(e) => setNidn(e.target.value)} maxLength={32} /></Field>
      <Field label="Email akun" hint="Dipakai untuk masuk ke Student Gateway dan, bila digunakan, AlurKerja."><input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required /></Field>
      <Field label="Email kontak"><input type="email" value={emailKontak} onChange={(e) => setEmailKontak(e.target.value)} /></Field>
      <Field label="Sandi" hint="Diisi langsung oleh admin dan diberikan kepada dosen secara aman."><input type="password" value={sandi} onChange={(e) => setSandi(e.target.value)} autoComplete="new-password" minLength={10} required /></Field>
      <button className="adm-btn" disabled={sibuk}>{sibuk ? 'Membuat akun…' : 'Buat akun dan tugaskan'}</button>
    </form>
  )
}

function FormPenugasan({ pohon, prodiId, onSelesai }: { pohon: ReturnType<typeof useStruktur>['pohon']; prodiId?: string; onSelesai: () => void }) {
  const { isSuper } = useStruktur()
  const [orang, setOrang] = useState<Orang | null>(null)
  const [peran, setPeran] = useState<Peran>(prodiId ? 'dosen_pa' : isSuper ? 'kaprodi' : 'dosen_pa')
  const [tipe, setTipe] = useState<UnitTipe>('prodi')
  const [unitId, setUnitId] = useState(prodiId ?? '')
  const [mulai, setMulai] = useState('')
  const { sibuk, galat, jalankan } = useAksi()

  const tipeSah = UNIT_SAH[peran]
  const tipeDipakai = tipeSah.includes(tipe) ? tipe : tipeSah[0]
  const pilihan = useMemo(() => {
    if (tipeDipakai === 'fakultas') return pohon.filter((f) => f.aktif).map((f) => ({ id: f.id, label: f.nama }))
    if (tipeDipakai === 'jurusan')
      return pohon.flatMap((f) => f.jurusan.filter((j) => j.aktif).map((j) => ({ id: j.id, label: `${f.nama} › ${j.nama}` })))
    if (tipeDipakai === 'prodi')
      return pohon.flatMap((f) => f.jurusan.flatMap((j) => j.prodi.filter((p) => p.aktif).map((p) => ({ id: p.id, label: `${j.nama} › ${p.nama}` }))))
    return []
  }, [pohon, tipeDipakai, prodiId])

  async function kirim(e: React.FormEvent) {
    e.preventDefault()
    if (!orang) return
    const r = await jalankan(() =>
      adminService.buatPenugasan({
        orang_id: orang.id,
        peran,
        unit_tipe: tipeDipakai,
        unit_id: tipeDipakai === 'global' ? null : unitId,
        mulai: mulai || null,
      }),
    )
    if (r) onSelesai()
  }

  const peranBoleh = prodiId ? (['dosen_pa'] as Peran[]) : isSuper ? PERAN : (['dosen_pa'] as Peran[])

  return (
    <form className="adm-form adm-boxed" onSubmit={kirim}>
      <h3>Penugasan baru</h3>
      {galat && <Notice tone="error">{galat}</Notice>}
      {/* Superadmin boleh memilih siapa saja; menyaring "dosen_pa" membuat orang baru tidak pernah bisa ditugaskan. */}
      <OrangPicker label={prodiId ? 'Dosen PA' : 'Orang'} peran={isSuper ? undefined : 'dosen_pa'} value={orang} onChange={setOrang} />
      {!prodiId && <Field label="Peran" hint={KETERANGAN[peran]}>
        <select value={peran} onChange={(e) => { const p = e.target.value as Peran; setPeran(p); setTipe(UNIT_SAH[p][0]); setUnitId('') }}>
          {peranBoleh.map((p) => <option key={p}>{p}</option>)}
        </select>
      </Field>}
      {!prodiId && tipeSah.length > 1 && (
        <Field label="Cakupan">
          <select value={tipeDipakai} onChange={(e) => { setTipe(e.target.value as UnitTipe); setUnitId('') }}>
            {tipeSah.map((t) => <option key={t}>{t}</option>)}
          </select>
        </Field>
      )}
      {tipeDipakai !== 'global' && (
        <Field label={`Unit (${tipeDipakai})`}>
          <select value={unitId} onChange={(e) => setUnitId(e.target.value)} required disabled={!!prodiId}>
            <option value="">Pilih…</option>
            {pilihan.map((o) => <option key={o.id} value={o.id}>{o.label}</option>)}
          </select>
        </Field>
      )}
      <Field label="Mulai" hint="Kosong = hari ini."><input type="date" value={mulai} onChange={(e) => setMulai(e.target.value)} /></Field>
      <button className="adm-btn" disabled={!orang || sibuk}>{sibuk ? 'Menyimpan…' : 'Simpan'}</button>
    </form>
  )
}
