'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Button, Modal, Space, Typography } from 'antd'
import { adminService, type Jenjang } from '@/src/services/admin-service'
import { Badge, Field, Kartu, Notice, useAksi, useStruktur } from './ui'

type Tipe = 'fakultas' | 'jurusan' | 'prodi'
interface FormState {
  tipe: Tipe
  /** id yang diubah; kosong = membuat baru */
  id?: string
  /** id induk (fakultas untuk jurusan, jurusan untuk prodi) */
  indukId?: string
  indukNama?: string
  kode: string
  nama: string
  jenjang: Jenjang
  maksSks: string
}

const JENJANG: Jenjang[] = ['D3', 'S1', 'S2', 'S3', 'Profesi']
const LABEL: Record<Tipe, string> = { fakultas: 'Fakultas', jurusan: 'Jurusan', prodi: 'Program studi' }

export function TabStruktur() {
  const { pohon, isSuper, muat } = useStruktur()
  const [form, setForm] = useState<FormState | null>(null)
  const { sibuk, galat, ok, jalankan, setGalat, setOk } = useAksi()

  function baru(tipe: Tipe, induk?: { id: string; nama: string }) {
    setOk('')
    setGalat('')
    setForm({ tipe, indukId: induk?.id, indukNama: induk?.nama, kode: '', nama: '', jenjang: 'S1', maksSks: '' })
  }

  async function ubah(tipe: Tipe, item: { id: string; kode: string; nama: string; jenjang?: Jenjang }) {
    setOk('')
    setGalat('')
    let maks: number | null = null
    if (tipe === 'prodi') {
      // Pohon struktur tidak memuat batas SKS; ambil dulu supaya menyimpan tidak mengosongkannya.
      const detail = await jalankan(() => adminService.ambilProdi(item.id))
      if (!detail) return
      maks = detail.maks_sks_semester
    }
    setForm({ tipe, id: item.id, kode: item.kode, nama: item.nama, jenjang: item.jenjang ?? 'S1', maksSks: maks ? String(maks) : '' })
  }

  async function simpan(e: React.FormEvent) {
    e.preventDefault()
    if (!form) return
    const f = form
    const maks = f.maksSks.trim() ? Number(f.maksSks) : null
    if (f.tipe === 'prodi' && maks !== null && (!Number.isInteger(maks) || maks < 1 || maks > 40)) {
      setGalat('Batas SKS harus bilangan bulat 1–40, atau kosong untuk bawaan (24).')
      return
    }
    const hasil = await jalankan(async () => {
      if (!f.id) {
        if (f.tipe === 'fakultas') await adminService.buatFakultas({ kode: f.kode.trim(), nama: f.nama.trim() })
        else if (f.tipe === 'jurusan') await adminService.buatJurusan({ fakultas_id: f.indukId!, kode: f.kode.trim(), nama: f.nama.trim() })
        else await adminService.buatProdi({ jurusan_id: f.indukId!, kode: f.kode.trim(), nama: f.nama.trim(), jenjang: f.jenjang, maks_sks_semester: maks })
      } else if (f.tipe === 'fakultas') await adminService.ubahFakultas(f.id, { nama: f.nama.trim() })
      else if (f.tipe === 'jurusan') await adminService.ubahJurusan(f.id, { nama: f.nama.trim() })
      else await adminService.ubahProdi(f.id, { nama: f.nama.trim(), jenjang: f.jenjang, maks_sks_semester: maks })
      await muat()
      return true
    }, `${LABEL[f.tipe]} disimpan.`)
    if (hasil) setForm(null)
  }

  async function aktifkan(tipe: Tipe, id: string, aktif: boolean) {
    await jalankan(async () => {
      if (tipe === 'fakultas') await adminService.ubahFakultas(id, { aktif })
      else if (tipe === 'jurusan') await adminService.ubahJurusan(id, { aktif })
      else await adminService.ubahProdi(id, { aktif })
      await muat()
    }, aktif ? 'Diaktifkan.' : 'Dinonaktifkan.')
  }

  return (
    <div className="adm-stack">
      {!isSuper && <Notice>Hanya superadmin yang dapat mengubah struktur. Anda dapat melihatnya di sini.</Notice>}
      {galat && <Notice tone="error" onClose={() => setGalat('')}>{galat}</Notice>}
      {ok && <Notice tone="ok" onClose={() => setOk('')}>{ok}</Notice>}

      {form && isSuper && (
        <Modal open title={`${form.id ? 'Ubah' : 'Tambah'} ${LABEL[form.tipe].toLowerCase()}${form.indukNama ? ` — di ${form.indukNama}` : ''}`} footer={null} onCancel={() => setForm(null)}>
          <form className="adm-form" onSubmit={simpan}>
            <Field label="Kode" hint={form.id ? 'Kode tidak dapat diubah.' : 'Huruf, angka, titik, garis bawah, atau tanda minus.'}>
              <input value={form.kode} onChange={(e) => setForm({ ...form, kode: e.target.value })} disabled={!!form.id} required maxLength={32} />
            </Field>
            <Field label="Nama">
              <input value={form.nama} onChange={(e) => setForm({ ...form, nama: e.target.value })} required maxLength={200} />
            </Field>
            {form.tipe === 'prodi' && (
              <>
                <Field label="Jenjang">
                  <select value={form.jenjang} onChange={(e) => setForm({ ...form, jenjang: e.target.value as Jenjang })}>
                    {JENJANG.map((j) => <option key={j}>{j}</option>)}
                  </select>
                </Field>
                <Field label="Batas SKS per semester" hint="Kosong = bawaan 24. Dipakai saat memangkas rencana studi.">
                  <input type="number" min={1} max={40} value={form.maksSks} onChange={(e) => setForm({ ...form, maksSks: e.target.value })} />
                </Field>
              </>
            )}
            <div className="adm-row">
              <button className="adm-btn" disabled={sibuk}>{sibuk ? 'Menyimpan…' : 'Simpan'}</button>
              <button type="button" className="adm-btn adm-ghost" onClick={() => setForm(null)}>Batal</button>
            </div>
          </form>
        </Modal>
      )}

      <Kartu
        judul="Fakultas, jurusan, dan program studi"
        aksi={isSuper ? <Button type="primary" onClick={() => baru('fakultas')}>+ Fakultas</Button> : undefined}
      >
        {pohon.length === 0 && <p className="adm-empty">Belum ada struktur. {isSuper ? 'Mulai dengan menambah fakultas.' : ''}</p>}
        <ul className="adm-tree">
          {pohon.map((f) => (
            <li key={f.id}>
              <div className="adm-node">
                <div className="structure-node-label"><Typography.Text strong>{f.nama}</Typography.Text><Typography.Text type="secondary">{f.kode}</Typography.Text>{!f.aktif && <Badge tone="merah">Nonaktif</Badge>}</div>
                {isSuper && (
                  <Space className="adm-actions" size={8} wrap>
                    <Button size="small" onClick={() => baru('jurusan', { id: f.id, nama: f.nama })}>+ Jurusan</Button>
                    <Button size="small" onClick={() => ubah('fakultas', f)}>Ubah</Button>
                    <Button size="small" danger={!f.aktif} disabled={sibuk} onClick={() => aktifkan('fakultas', f.id, !f.aktif)}>{f.aktif ? 'Nonaktifkan' : 'Aktifkan'}</Button>
                  </Space>
                )}
              </div>
              <ul>
                {f.jurusan.map((j) => (
                  <li key={j.id}>
                    <div className="adm-node">
                      <div className="structure-node-label"><Typography.Text>{j.nama}</Typography.Text><Typography.Text type="secondary">{j.kode}</Typography.Text>{!j.aktif && <Badge tone="merah">Nonaktif</Badge>}</div>
                      {isSuper && (
                        <Space className="adm-actions" size={8} wrap>
                          <Button size="small" type="primary" ghost onClick={() => baru('prodi', { id: j.id, nama: j.nama })}>+ Prodi</Button>
                          <Button size="small" onClick={() => ubah('jurusan', j)}>Ubah</Button>
                          <Button size="small" danger={!j.aktif} disabled={sibuk} onClick={() => aktifkan('jurusan', j.id, !j.aktif)}>{j.aktif ? 'Nonaktifkan' : 'Aktifkan'}</Button>
                        </Space>
                      )}
                    </div>
                    <ul>
                      {j.prodi.map((p) => (
                        <li key={p.id}>
                          <div className="adm-node">
                            <div className="structure-node-label"><Typography.Link href={`/admin/struktur/prodi/${p.id}`} strong>{p.nama}</Typography.Link><Typography.Text type="secondary">{p.kode} · {p.jenjang}</Typography.Text>{!p.aktif && <Badge tone="merah">Nonaktif</Badge>}</div>
                            {isSuper && (
                              <Space className="adm-actions" size={8} wrap>
                                <Button size="small" onClick={() => ubah('prodi', p)}>Ubah</Button>
                                <Button size="small" danger={!p.aktif} disabled={sibuk} onClick={() => aktifkan('prodi', p.id, !p.aktif)}>{p.aktif ? 'Nonaktifkan' : 'Aktifkan'}</Button>
                              </Space>
                            )}
                          </div>
                        </li>
                      ))}
                    </ul>
                  </li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
      </Kartu>
    </div>
  )
}
