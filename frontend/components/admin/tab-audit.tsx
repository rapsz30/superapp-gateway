'use client'

import { Fragment, useState } from 'react'
import { adminService } from '@/src/services/admin-service'
import { Field, Kartu, Kosong, Notice, Pager, useLoad, useOrang, waktu } from './ui'

const UKURAN = 30

export function TabAudit() {
  const [aksi, setAksi] = useState('')
  const [cari, setCari] = useState('')
  const [halaman, setHalaman] = useState(1)
  const [terbuka, setTerbuka] = useState<number | null>(null)

  const daftar = useLoad(() => adminService.daftarAudit({ aksi: cari || undefined, halaman, ukuran: UKURAN }), [cari, halaman])
  const nama = useOrang((daftar.data?.data ?? []).map((a) => a.pelaku_id))

  return (
    <div className="adm-stack">
      <Kartu judul="Jejak audit">
        <p className="adm-muted">Semua perubahan data tercatat dan tidak dapat diubah atau dihapus. Hanya superadmin yang dapat melihatnya.</p>
        <form className="adm-filter" onSubmit={(e) => { e.preventDefault(); setHalaman(1); setCari(aksi.trim()) }}>
          <Field label="Aksi (persis)" hint="Contoh: panduan.aktifkan, akun.buat, bimbingan.buat"><input value={aksi} onChange={(e) => setAksi(e.target.value)} /></Field>
          <button className="adm-btn">Terapkan</button>
        </form>
        {daftar.error && <Notice tone="error">{daftar.error}</Notice>}
        {daftar.loading && !daftar.data && <Kosong>Memuat…</Kosong>}
        {daftar.data && daftar.data.data.length === 0 && <Kosong>Tidak ada catatan.</Kosong>}
        {daftar.data && daftar.data.data.length > 0 && (
          <div className="adm-scroll">
            <table className="adm-table">
              <thead><tr><th>Waktu</th><th>Pelaku</th><th>Aksi</th><th>Objek</th><th /></tr></thead>
              <tbody>
                {daftar.data.data.map((a) => (
                  <Fragment key={a.id}>
                    <tr>
                      <td>{waktu(a.waktu)}</td>
                      <td>{a.pelaku_id ? nama(a.pelaku_id) : <span className="adm-muted">sistem</span>}</td>
                      <td><code>{a.aksi}</code></td>
                      <td>{a.objek_tipe}</td>
                      <td><button className="adm-link" onClick={() => setTerbuka(terbuka === a.id ? null : a.id)}>{terbuka === a.id ? 'Tutup' : 'Rincian'}</button></td>
                    </tr>
                    {terbuka === a.id && (
                      <tr className="adm-detail">
                        <td colSpan={5}>
                          <div className="adm-grid2">
                            <div><h3>Sebelum</h3><pre>{a.sebelum ? JSON.stringify(a.sebelum, null, 2) : '—'}</pre></div>
                            <div><h3>Sesudah</h3><pre>{a.sesudah ? JSON.stringify(a.sesudah, null, 2) : '—'}</pre></div>
                          </div>
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
