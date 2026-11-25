'use client'

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { Alert, Button as AntButton, Card, Empty, Form, Input, Pagination, Select, Tag, Modal } from 'antd'
import { adminService, type Orang, type StrukturFakultas } from '@/src/services/admin-service'
import { errorMessage } from '@/src/lib/api'

// ---------- Struktur (dibagi ke semua tab) ----------
export interface UnitInfo { id: string; nama: string; kode: string; tipe: 'fakultas' | 'jurusan' | 'prodi'; jalur: string; aktif: boolean }

interface StrukturCtx {
  pohon: StrukturFakultas[]
  unit: Map<string, UnitInfo>
  prodi: UnitInfo[]
  isSuper: boolean
  muat: () => Promise<void>
}

const Ctx = createContext<StrukturCtx | null>(null)

export function StrukturProvider({ isSuper, children }: { isSuper: boolean; children: ReactNode }) {
  const [pohon, setPohon] = useState<StrukturFakultas[]>([])
  const [galat, setGalat] = useState('')
  const muat = useCallback(async () => {
    try {
      setPohon(await adminService.struktur(true))
      setGalat('')
    } catch (e) {
      setGalat(errorMessage(e))
    }
  }, [])
  useEffect(() => {
    void muat()
  }, [muat])

  const nilai = useMemo<StrukturCtx>(() => {
    const unit = new Map<string, UnitInfo>()
    const prodi: UnitInfo[] = []
    for (const f of pohon) {
      unit.set(f.id, { id: f.id, nama: f.nama, kode: f.kode, tipe: 'fakultas', jalur: f.nama, aktif: f.aktif })
      for (const j of f.jurusan) {
        unit.set(j.id, { id: j.id, nama: j.nama, kode: j.kode, tipe: 'jurusan', jalur: `${f.nama} › ${j.nama}`, aktif: j.aktif })
        for (const p of j.prodi) {
          const u: UnitInfo = { id: p.id, nama: p.nama, kode: p.kode, tipe: 'prodi', jalur: `${j.nama} › ${p.nama}`, aktif: p.aktif }
          unit.set(p.id, u)
          prodi.push(u)
        }
      }
    }
    return { pohon, unit, prodi, isSuper, muat }
  }, [pohon, isSuper, muat])

  return (
    <Ctx.Provider value={nilai}>
      {galat && <Notice tone="error">Struktur gagal dimuat: {galat}</Notice>}
      {children}
    </Ctx.Provider>
  )
}

export function useStruktur(): StrukturCtx {
  const v = useContext(Ctx)
  if (!v) throw new Error('useStruktur di luar StrukturProvider')
  return v
}

export const namaUnit = (unit: Map<string, UnitInfo>, id: string | null | undefined) =>
  id ? (unit.get(id)?.nama ?? 'unit tidak dikenal') : '—'

// ---------- Pemuatan data ----------
export function useLoad<T>(fn: () => Promise<T>, deps: unknown[]) {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const urut = useRef(0)
  const fnRef = useRef(fn)
  fnRef.current = fn

  const reload = useCallback(async () => {
    const saya = ++urut.current
    setLoading(true)
    try {
      const hasil = await fnRef.current()
      if (saya === urut.current) {
        setData(hasil)
        setError('')
      }
    } catch (e) {
      if (saya === urut.current) setError(errorMessage(e))
    } finally {
      if (saya === urut.current) setLoading(false)
    }
  }, [])

  useEffect(() => {
    void reload()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  return { data, loading, error, reload }
}

/** Nama orang untuk daftar id (diambil satu per satu dan disimpan di cache modul). */
const cacheOrang = new Map<string, Orang>()
export function useOrang(ids: (string | null | undefined)[]) {
  const [, paksa] = useState(0)
  const kunci = Array.from(new Set(ids.filter((x): x is string => !!x))).sort().join(',')
  useEffect(() => {
    let aktif = true
    const perlu = kunci ? kunci.split(',').filter((id) => !cacheOrang.has(id)) : []
    if (!perlu.length) return
    void (async () => {
      for (const id of perlu) {
        try {
          cacheOrang.set(id, await adminService.ambilOrang(id))
        } catch {
          /* dibiarkan: tampil sebagai id pendek */
        }
      }
      if (aktif) paksa((n) => n + 1)
    })()
    return () => {
      aktif = false
    }
  }, [kunci])
  return (id: string | null | undefined): string => {
    if (!id) return '—'
    const o = cacheOrang.get(id)
    return o ? o.nama_lengkap : `${id.slice(0, 8)}…`
  }
}
export function lupakanOrang(id: string) {
  cacheOrang.delete(id)
}

/** Konfirmasi non-blocking agar dialog tetap bisa dipakai dari browser automation. */
export function konfirmasi(content: string, title = 'Konfirmasi tindakan') {
  return new Promise<boolean>((resolve) => {
    Modal.confirm({
      title,
      content,
      okText: 'Lanjutkan',
      cancelText: 'Batal',
      onOk: () => resolve(true),
      onCancel: () => resolve(false),
    })
  })
}

// ---------- Komponen kecil ----------
export function Notice({ tone = 'info', children, onClose }: { tone?: 'info' | 'error' | 'ok'; children: ReactNode; onClose?: () => void }) {
  return <Alert className="adm-notice" type={tone === 'ok' ? 'success' : tone === 'error' ? 'error' : 'info'} message={children} closable={!!onClose} onClose={onClose} />
}

export function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return <Form.Item className="adm-field" label={label} extra={hint}>{children}</Form.Item>
}

export function Badge({ tone = 'abu', children }: { tone?: 'abu' | 'hijau' | 'kuning' | 'merah' | 'biru'; children: ReactNode }) {
  const color = tone === 'hijau' ? 'success' : tone === 'kuning' ? 'warning' : tone === 'merah' ? 'error' : tone === 'biru' ? 'blue' : undefined
  return <Tag color={color}>{children}</Tag>
}

export function Pager({ halaman, ukuran, total, onChange }: { halaman: number; ukuran: number; total: number; onChange: (h: number) => void }) {
  return <div className="adm-pager"><span>{total} data</span><Pagination current={halaman} pageSize={ukuran} total={total} hideOnSinglePage showSizeChanger={false} onChange={onChange} /></div>
}

export function Kosong({ children }: { children: ReactNode }) {
  return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={children} />
}

export function Kartu({ judul, aksi, children }: { judul: string; aksi?: ReactNode; children: ReactNode }) {
  return <Card className="adm-card" title={judul} extra={aksi}>{children}</Card>
}

/** Jalankan aksi dengan penanda sibuk dan pesan galat/sukses. */
export function useAksi() {
  const [sibuk, setSibuk] = useState(false)
  const [galat, setGalat] = useState('')
  const [ok, setOk] = useState('')
  const jalankan = useCallback(async <T,>(fn: () => Promise<T>, pesanOk?: string): Promise<T | undefined> => {
    setSibuk(true)
    setGalat('')
    setOk('')
    try {
      const hasil = await fn()
      if (pesanOk) setOk(pesanOk)
      return hasil
    } catch (e) {
      setGalat(errorMessage(e))
      return undefined
    } finally {
      setSibuk(false)
    }
  }, [])
  return { sibuk, galat, ok, jalankan, setGalat, setOk }
}

/** Kotak sandi sementara: tampil sekali, dengan tombol salin. */
export function SandiSementara({ email, sandi, onClose }: { email: string; sandi: string; onClose: () => void }) {
  const [tersalin, setTersalin] = useState(false)
  return (
    <Alert className="adm-secret" type="warning" showIcon message={`Sandi sementara untuk ${email}`} description={<><p>Sandi ini hanya tampil sekali dan tidak dapat dilihat lagi. Berikan kepada pemiliknya; ia wajib menggantinya saat masuk pertama.</p><code>{sandi}</code><div className="adm-row">
        <AntButton type="primary"
          onClick={() => {
            void navigator.clipboard?.writeText(sandi).then(() => setTersalin(true)).catch(() => undefined)
          }}
        >
          {tersalin ? 'Tersalin' : 'Salin'}
        </AntButton>
        <AntButton onClick={onClose}>Sudah saya catat</AntButton>
      </div></>} />
  )
}

/** Cari orang berdasarkan nama, NIM, atau NIDN. */
export function OrangPicker({
  label,
  peran,
  prodiId,
  value,
  onChange,
}: {
  label: string
  peran?: string
  prodiId?: string
  value: Orang | null
  onChange: (o: Orang | null) => void
}) {
  const [q, setQ] = useState('')
  const [hasil, setHasil] = useState<Orang[]>([])
  const [buka, setBuka] = useState(false)
  const [galat, setGalat] = useState('')
  const urut = useRef(0)

  useEffect(() => {
    if (!buka) return
    const saya = ++urut.current
    const t = setTimeout(async () => {
      try {
        const r = await adminService.daftarOrang({ q: q.trim() || undefined, peran, prodi_id: prodiId, ukuran: 8 })
        if (saya === urut.current) {
          setHasil(r.data)
          setGalat('')
        }
      } catch (e) {
        if (saya === urut.current) setGalat(errorMessage(e))
      }
    }, 250)
    return () => clearTimeout(t)
  }, [q, buka, peran, prodiId])

  if (value) {
    return (
      <div className="adm-field">
        <span>{label}</span>
        <div className="adm-picked">
          <span>
            {value.nama_lengkap}
            <small> {value.nim ?? value.nidn ?? ''}</small>
          </span>
          <AntButton type="link" onClick={() => onChange(null)}>Ganti</AntButton>
        </div>
      </div>
    )
  }
  return (
    <div className="adm-field">
      <span>{label}</span>
      <Input
        value={q}
        onChange={(e) => { setQ(e.target.value); setBuka(true) }}
        onFocus={() => setBuka(true)}
        placeholder="Ketik nama, NIM, atau NIDN"
        aria-label={label}
      />
      {buka && (
        <ul className="adm-suggest">
          {galat && <li className="adm-err">{galat}</li>}
          {!galat && hasil.length === 0 && <li className="adm-muted">Tidak ada hasil.</li>}
          {hasil.map((o) => (
            <li key={o.id}>
              <AntButton type="text" block onClick={() => { onChange(o); setBuka(false); setQ('') }}>
                {o.nama_lengkap}
                <small> {o.nim ?? o.nidn ?? ''}{o.peran.length ? ` · ${o.peran.join(', ')}` : ''}</small>
              </AntButton>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export const tanggal = (s: string | null | undefined) => (s ? s.slice(0, 10) : '—')
export const waktu = (s: string) => new Date(s).toLocaleString('id-ID', { dateStyle: 'medium', timeStyle: 'short' })

export function SelectProdi({ value, onChange, label = 'Program studi', kosong = 'Pilih program studi', aktifSaja = true }: {
  value: string
  onChange: (v: string) => void
  label?: string
  kosong?: string
  aktifSaja?: boolean
}) {
  const { prodi } = useStruktur()
  const daftar = aktifSaja ? prodi.filter((p) => p.aktif) : prodi
  return (
    <Field label={label}>
      <Select value={value || undefined} placeholder={kosong} allowClear onChange={(next) => onChange(next ?? '')} options={daftar.map((p) => ({ value: p.id, label: `${p.jalur}${p.aktif ? '' : ' (nonaktif)'}` }))} />
    </Field>
  )
}
