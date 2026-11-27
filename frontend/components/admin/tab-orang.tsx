'use client'

import { Fragment, useState } from 'react'
import { Modal } from 'antd'
import { adminService, type Akun, type ImporLaporan, type Orang } from '@/src/services/admin-service'
import { Badge, Field, Kartu, Kosong, Notice, Pager, SandiSementara, SelectProdi, lupakanOrang, namaUnit, tanggal, useAksi, useKonfirmasi, useLoad, useStruktur } from './ui'

const PERAN = ['mahasiswa', 'dosen_pa', 'kaprodi', 'kajur', 'dekan', 'superadmin']
const UKURAN = 20

export function TabOrang() {
  const { isSuper } = useStruktur()
  const [q, setQ] = useState('')
  const [cari, setCari] = useState('')
  const [peran, setPeran] = useState('')
  const [prodiId, setProdiId] = useState('')
  const [halaman, setHalaman] = useState(1)
  const [terbuka, setTerbuka] = useState<string | null>(null)
  const [baru, setBaru] = useState(false)
  const [impor, setImpor] = useState(false)
  const [rahasia, setRahasia] = useState<{ email: string; sandi: string } | null>(null)

  const daftar = useLoad(
    () => adminService.daftarOrang({ q: cari || undefined, peran: peran || undefined, prodi_id: prodiId || undefined, halaman, ukuran: UKURAN }),
    [cari, peran, prodiId, halaman],
  )

  return (
    <div className="adm-stack">
      {rahasia && <SandiSementara email={rahasia.email} sandi={rahasia.sandi} onClose={() => setRahasia(null)} />}

      <Kartu
        judul="Orang dan akun"
        aksi={
          isSuper ? (
            <div className="adm-row">
              <button className="adm-btn adm-ghost" onClick={() => { setImpor(!impor); setBaru(false) }}>Impor CSV</button>
              <button className="adm-btn" onClick={() => { setBaru(!baru); setImpor(false) }}>+ Orang</button>
            </div>
          ) : undefined
        }
      >
        {baru && isSuper && <Modal open title="Tambah orang" footer={null} onCancel={() => setBaru(false)}><FormOrang onSelesai={(o) => { setBaru(false); setTerbuka(o?.id ?? null); void daftar.reload() }} /></Modal>}
        {impor && isSuper && <Modal open title="Impor orang dari CSV" footer={null} width={760} onCancel={() => setImpor(false)}><FormImpor onSelesai={() => void daftar.reload()} /></Modal>}

        <form
          className="adm-filter"
          onSubmit={(e) => { e.preventDefault(); setHalaman(1); setCari(q.trim()) }}
        >
          <Field label="Cari">
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Nama, NIM, atau NIDN" />
          </Field>
          <Field label="Peran">
            <select value={peran} onChange={(e) => { setHalaman(1); setPeran(e.target.value) }}>
              <option value="">Semua</option>
              {PERAN.map((p) => <option key={p}>{p}</option>)}
            </select>
          </Field>
          <SelectProdi value={prodiId} onChange={(v) => { setHalaman(1); setProdiId(v) }} label="Prodi" kosong="Semua prodi" aktifSaja={false} />
          <button className="adm-btn">Cari</button>
        </form>

        {daftar.error && <Notice tone="error">{daftar.error}</Notice>}
        {daftar.loading && !daftar.data && <Kosong>Memuat…</Kosong>}
        {daftar.data && daftar.data.data.length === 0 && <Kosong>Tidak ada orang yang cocok.</Kosong>}
        {daftar.data && daftar.data.data.length > 0 && (
          <div className="adm-scroll">
            <table className="adm-table">
              <thead>
                <tr><th>Nama</th><th>NIM / NIDN</th><th>Prodi isian</th><th>Perguruan tinggi</th><th>Peran</th><th>Akun</th><th /></tr>
              </thead>
              <tbody>
                {daftar.data.data.map((o) => (
                  <Fragment key={o.id}>
                    <tr>
                      <td>{o.nama_lengkap}</td>
                      <td>{o.nim ?? o.nidn ?? '—'}</td>
                      <td>{o.prodi_isian ?? '—'}</td>
                      <td>{o.pt_isian ?? '—'}</td>
                      <td>{o.peran.length ? o.peran.map((p) => <Badge key={p} tone="biru">{p}</Badge>) : <span className="adm-muted">—</span>}</td>
                      <td>
                        {o.akun ? (
                          <>{o.akun.email} <Badge tone={o.akun.status === 'aktif' ? 'hijau' : 'kuning'}>{o.akun.status}</Badge></>
                        ) : (
                          <span className="adm-muted">belum ada akun</span>
                        )}
                      </td>
                      <td><button className="adm-link" onClick={() => setTerbuka(terbuka === o.id ? null : o.id)}>{terbuka === o.id ? 'Tutup' : 'Kelola'}</button></td>
                    </tr>
                    {terbuka === o.id && (
                      <tr className="adm-detail">
                        <td colSpan={5}>
                          <DetailOrang orang={o} onUbah={() => void daftar.reload()} onRahasia={setRahasia} />
                        </td>
                      </tr>
                    )}
                  </Fragment>
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

function FormOrang({ onSelesai }: { onSelesai: (o: Orang | null) => void }) {
  const [nama, setNama] = useState('')
  const [nim, setNim] = useState('')
  const [nidn, setNidn] = useState('')
  const [email, setEmail] = useState('')
  const { sibuk, galat, jalankan } = useAksi()

  async function kirim(e: React.FormEvent) {
    e.preventDefault()
    const o = await jalankan(() =>
      adminService.buatOrang({
        nama_lengkap: nama.trim(),
        nim: nim.trim() || null,
        nidn: nidn.trim() || null,
        email_kontak: email.trim() || null,
      }),
    )
    if (o) onSelesai(o)
  }

  return (
    <form className="adm-form adm-boxed" onSubmit={kirim}>
      <h3>Orang baru</h3>
      {galat && <Notice tone="error">{galat}</Notice>}
      <Field label="Nama lengkap"><input value={nama} onChange={(e) => setNama(e.target.value)} required maxLength={200} /></Field>
      <Field label="NIM" hint="Isi untuk mahasiswa."><input value={nim} onChange={(e) => setNim(e.target.value)} maxLength={32} /></Field>
      <Field label="NIDN" hint="Isi untuk dosen."><input value={nidn} onChange={(e) => setNidn(e.target.value)} maxLength={32} /></Field>
      <Field label="Email kontak"><input type="email" value={email} onChange={(e) => setEmail(e.target.value)} /></Field>
      <div className="adm-row">
        <button className="adm-btn" disabled={sibuk}>{sibuk ? 'Menyimpan…' : 'Simpan'}</button>
        <button type="button" className="adm-btn adm-ghost" onClick={() => onSelesai(null)}>Batal</button>
      </div>
    </form>
  )
}

function FormImpor({ onSelesai }: { onSelesai: () => void }) {
  const [berkas, setBerkas] = useState<File | null>(null)
  const [laporan, setLaporan] = useState<ImporLaporan | null>(null)
  const { sibuk, galat, jalankan } = useAksi()

  async function kirim(e: React.FormEvent) {
    e.preventDefault()
    if (!berkas) return
    const r = await jalankan(() => adminService.imporOrang(berkas))
    if (r) {
      setLaporan(r)
      onSelesai()
    }
  }

  return (
    <div className="adm-boxed">
      <h3>Impor CSV</h3>
      <p className="adm-muted">
        Kolom: <code>nama_lengkap</code> (wajib), <code>nim</code>, <code>nidn</code>, <code>email_kontak</code>, <code>email_akun</code>,{' '}
        <code>prodi</code> (<code>KODE_FAKULTAS/KODE_JURUSAN/KODE_PRODI</code>), <code>angkatan</code>. Berenkode UTF-8, maksimal 2 MB. Baris yang gagal tidak menggagalkan yang lain.
      </p>
      <form className="adm-row" onSubmit={kirim}>
        <input type="file" accept=".csv,text/csv" onChange={(e) => { setBerkas(e.target.files?.[0] ?? null); setLaporan(null) }} />
        <button className="adm-btn" disabled={!berkas || sibuk}>{sibuk ? 'Mengimpor…' : 'Impor'}</button>
      </form>
      {galat && <Notice tone="error">{galat}</Notice>}
      {laporan && (
        <>
          <Notice tone={laporan.gagal ? 'info' : 'ok'}>{laporan.berhasil} berhasil, {laporan.gagal} gagal dari {laporan.total} baris.</Notice>
          {laporan.baris.some((b) => b.sandi_sementara) && (
            <Notice tone="error">Sandi sementara di bawah hanya tampil sekali. Catat sebelum menutup halaman ini.</Notice>
          )}
          <div className="adm-scroll">
            <table className="adm-table">
              <thead><tr><th>Baris</th><th>Status</th><th>Email</th><th>Sandi sementara</th><th>Keterangan</th></tr></thead>
              <tbody>
                {laporan.baris.map((b, i) => (
                  <tr key={i}>
                    <td>{b.baris ?? i + 2}</td>
                    <td><Badge tone={b.status === 'ok' ? 'hijau' : 'merah'}>{b.status}</Badge></td>
                    <td>{b.email ?? ''}</td>
                    <td>{b.sandi_sementara ? <code>{b.sandi_sementara}</code> : ''}</td>
                    <td>{b.alasan ?? ''}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}

function DetailOrang({ orang, onUbah, onRahasia }: { orang: Orang; onUbah: () => void; onRahasia: (r: { email: string; sandi: string }) => void }) {
  const konfirmasi = useKonfirmasi()
  const { isSuper, unit } = useStruktur()
  const { sibuk, galat, ok, jalankan, setGalat, setOk } = useAksi()
  const [email, setEmail] = useState(orang.email_kontak ?? '')
  const [emailAkun, setEmailAkun] = useState(orang.email_kontak ?? '')
  const [sandi, setSandi] = useState('')
  const [nama, setNama] = useState(orang.nama_lengkap)
  const [nim, setNim] = useState(orang.nim ?? '')
  const [nidn, setNidn] = useState(orang.nidn ?? '')
  const [prodiBaru, setProdiBaru] = useState('')
  const [angkatan, setAngkatan] = useState('')
  const [pindahKe, setPindahKe] = useState<{ id: string; prodi: string } | null>(null)
  const [akunBuka, setAkunBuka] = useState(false)
  const [keanggotaanBuka, setKeanggotaanBuka] = useState(false)

  const keanggotaan = useLoad(() => adminService.daftarKeanggotaan({ orang_id: orang.id, ukuran: 50 }), [orang.id])

  async function simpanData(e: React.FormEvent) {
    e.preventDefault()
    const o = await jalankan(
      () => adminService.ubahOrang(orang.id, { nama_lengkap: nama.trim(), nim: nim.trim() || null, nidn: nidn.trim() || null, email_kontak: email.trim() || null }),
      'Data disimpan.',
    )
    if (o) {
      lupakanOrang(orang.id)
      onUbah()
    }
  }

  function tampilkanSandi(a: Akun) {
    if (a.sandi_sementara) onRahasia({ email: a.email, sandi: a.sandi_sementara })
  }

  async function buatAkun(e: React.FormEvent) {
    e.preventDefault()
    const a = await jalankan(() => adminService.buatAkun({ orang_id: orang.id, email: emailAkun.trim(), sandi: sandi || null }), 'Akun dibuat.')
    if (a) {
      tampilkanSandi(a)
      setSandi('')
      setAkunBuka(false)
      lupakanOrang(orang.id)
      onUbah()
    }
  }

  async function aturUlang() {
    if (!orang.akun || !(await konfirmasi(`Atur ulang sandi ${orang.akun.email}? Semua sesinya akan keluar.`))) return
    const a = await jalankan(() => adminService.aturUlangSandi(orang.akun!.id), 'Sandi diatur ulang.')
    if (a) {
      tampilkanSandi(a)
      onUbah()
    }
  }

  async function ubahStatus(status: 'aktif' | 'ditangguhkan' | 'nonaktif') {
    if (!orang.akun) return
    const a = await jalankan(() => adminService.ubahStatusAkun(orang.akun!.id, status), `Akun ${status}.`)
    if (a) {
      lupakanOrang(orang.id)
      onUbah()
    }
  }

  async function tambahKeanggotaan(e: React.FormEvent) {
    e.preventDefault()
    const th = angkatan.trim() ? Number(angkatan) : null
    const k = await jalankan(() => adminService.buatKeanggotaan({ orang_id: orang.id, prodi_id: prodiBaru, angkatan: th }), 'Mahasiswa didaftarkan ke prodi.')
    if (k) {
      setProdiBaru('')
      setAngkatan('')
      setKeanggotaanBuka(false)
      void keanggotaan.reload()
      onUbah()
    }
  }

  async function statusKeanggotaan(id: string, status: 'aktif' | 'cuti' | 'lulus' | 'keluar') {
    if ((status === 'lulus' || status === 'keluar') && !(await konfirmasi(`Tandai ${status}? Bimbingan dan pengajuan yang berjalan akan dihentikan.`))) return
    const k = await jalankan(() => adminService.ubahStatusKeanggotaan(id, status), `Status menjadi ${status}.`)
    if (k) {
      void keanggotaan.reload()
      onUbah()
    }
  }

  async function pindah() {
    if (!pindahKe?.prodi) return
    if (!(await konfirmasi('Pindahkan prodi? Bimbingan dan pengajuan yang berjalan akan dihentikan.'))) return
    const k = await jalankan(() => adminService.pindahProdi(pindahKe.id, { prodi_tujuan_id: pindahKe.prodi }), 'Prodi dipindahkan.')
    if (k) {
      setPindahKe(null)
      void keanggotaan.reload()
      onUbah()
    }
  }

  const aktifSekarang = keanggotaan.data?.data.find((k) => !k.selesai)

  return (
    <div className="adm-grid2">
      {galat && <div className="adm-span"><Notice tone="error" onClose={() => setGalat('')}>{galat}</Notice></div>}
      {ok && <div className="adm-span"><Notice tone="ok" onClose={() => setOk('')}>{ok}</Notice></div>}

      <div>
        <h3>Data</h3>
        {isSuper ? (
          <form className="adm-form" onSubmit={simpanData}>
            <Field label="Nama lengkap"><input value={nama} onChange={(e) => setNama(e.target.value)} required /></Field>
            <Field label="NIM"><input value={nim} onChange={(e) => setNim(e.target.value)} /></Field>
            <Field label="NIDN"><input value={nidn} onChange={(e) => setNidn(e.target.value)} /></Field>
            <Field label="Email kontak"><input type="email" value={email} onChange={(e) => setEmail(e.target.value)} /></Field>
            <button className="adm-btn" disabled={sibuk}>Simpan data</button>
          </form>
        ) : (
          <p className="adm-muted">Hanya superadmin yang dapat mengubah data orang.</p>
        )}
      </div>

      <div>
        <h3>Akun</h3>
        {orang.akun ? (
          <div className="adm-stack">
            <p>{orang.akun.email} <Badge tone={orang.akun.status === 'aktif' ? 'hijau' : 'kuning'}>{orang.akun.status}</Badge> {orang.akun.wajib_ganti_sandi && <Badge tone="kuning">wajib ganti sandi</Badge>}</p>
            {isSuper && (
              <div className="adm-row">
                <button className="adm-btn adm-ghost" disabled={sibuk} onClick={aturUlang}>Atur ulang sandi</button>
                {orang.akun.status !== 'aktif' && <button className="adm-btn adm-ghost" disabled={sibuk} onClick={() => ubahStatus('aktif')}>Aktifkan</button>}
                {orang.akun.status === 'aktif' && <button className="adm-btn adm-ghost" disabled={sibuk} onClick={() => ubahStatus('ditangguhkan')}>Tangguhkan</button>}
                {orang.akun.status !== 'nonaktif' && <button className="adm-btn adm-danger" disabled={sibuk} onClick={() => void konfirmasi('Nonaktifkan akun ini?').then((setuju) => { if (setuju) void ubahStatus('nonaktif') })}>Nonaktifkan</button>}
              </div>
            )}
          </div>
        ) : isSuper ? (
          <>
            <button className="adm-btn" onClick={() => setAkunBuka(true)}>+ Buat akun</button>
            <Modal open={akunBuka} title="Buat akun" footer={null} onCancel={() => setAkunBuka(false)}>
          <form className="adm-form" onSubmit={buatAkun}>
            <Field label="Email akun" hint="Dipakai untuk masuk. Untuk dosen, samakan dengan akun AlurKerja-nya."><input type="email" value={emailAkun} onChange={(e) => setEmailAkun(e.target.value)} required /></Field>
            <Field label="Sandi awal" hint="Kosongkan agar dibuat otomatis (ditampilkan sekali)."><input type="text" value={sandi} onChange={(e) => setSandi(e.target.value)} autoComplete="off" /></Field>
            <button className="adm-btn" disabled={sibuk}>Buat akun</button>
          </form>
            </Modal>
          </>
        ) : (
          <p className="adm-muted">Belum ada akun.</p>
        )}
      </div>

      <div className="adm-span">
        <h3>Keanggotaan program studi (mahasiswa)</h3>
        {keanggotaan.error && <Notice tone="error">{keanggotaan.error}</Notice>}
        {keanggotaan.data && keanggotaan.data.data.length === 0 && <p className="adm-muted">Belum terdaftar di prodi mana pun.</p>}
        {keanggotaan.data && keanggotaan.data.data.length > 0 && (
          <div className="adm-scroll">
            <table className="adm-table">
              <thead><tr><th>Prodi</th><th>Angkatan</th><th>Status</th><th>Mulai</th><th>Selesai</th><th /></tr></thead>
              <tbody>
                {keanggotaan.data.data.map((k) => (
                  <tr key={k.id}>
                    <td>{namaUnit(unit, k.prodi_id)}</td>
                    <td>{k.angkatan ?? '—'}</td>
                    <td><Badge tone={k.selesai ? 'abu' : 'hijau'}>{k.status}</Badge></td>
                    <td>{tanggal(k.mulai)}</td>
                    <td>{tanggal(k.selesai)}</td>
                    <td>
                      {!k.selesai && (
                        <div className="adm-row">
                          {k.status === 'aktif' && <button className="adm-link" onClick={() => statusKeanggotaan(k.id, 'cuti')}>Cuti</button>}
                          {k.status === 'cuti' && <button className="adm-link" onClick={() => statusKeanggotaan(k.id, 'aktif')}>Aktifkan</button>}
                          <button className="adm-link" onClick={() => statusKeanggotaan(k.id, 'lulus')}>Lulus</button>
                          <button className="adm-link" onClick={() => statusKeanggotaan(k.id, 'keluar')}>Keluar</button>
                          {isSuper && <button className="adm-link" onClick={() => setPindahKe({ id: k.id, prodi: '' })}>Pindah prodi</button>}
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {pindahKe && (
          <Modal open title="Pindah program studi" footer={null} onCancel={() => setPindahKe(null)}>
            <SelectProdi value={pindahKe.prodi} onChange={(v) => setPindahKe({ ...pindahKe, prodi: v })} label="Prodi tujuan" />
            <div className="adm-row">
              <button className="adm-btn" disabled={!pindahKe.prodi || sibuk} onClick={pindah}>Pindahkan</button>
              <button className="adm-btn adm-ghost" onClick={() => setPindahKe(null)}>Batal</button>
            </div>
          </Modal>
        )}
        {keanggotaan.data && !aktifSekarang && (
          <>
            <button className="adm-btn" onClick={() => setKeanggotaanBuka(true)}>+ Daftarkan ke prodi</button>
            <Modal open={keanggotaanBuka} title="Daftarkan ke program studi" footer={null} onCancel={() => setKeanggotaanBuka(false)}>
              <form className="adm-form" onSubmit={tambahKeanggotaan}>
                <SelectProdi value={prodiBaru} onChange={setProdiBaru} label="Daftarkan ke prodi" />
                <Field label="Angkatan"><input type="number" min={1990} max={2100} value={angkatan} onChange={(e) => setAngkatan(e.target.value)} placeholder="mis. 2022" /></Field>
                <button className="adm-btn" disabled={!prodiBaru || sibuk}>Daftarkan</button>
              </form>
            </Modal>
          </>
        )}
      </div>
    </div>
  )
}
