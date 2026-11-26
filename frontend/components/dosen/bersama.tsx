'use client'
import { useCallback, useEffect, useRef, useState } from 'react'
import { Tag } from 'antd'
import { errorMessage } from '@/src/lib/api'
import type { Submission } from '@/src/services/pengajuan-service'

/**
 * Muat data, lalu segarkan berkala supaya kemajuan proses AlurKerja terlihat tanpa muat ulang halaman.
 * `kunci` berubah berarti data lain: hasil lama dibuang.
 */
export function useMuat<T>(kunci: string, ambil: () => Promise<T>, jedaMs = 20_000) {
  const [data, setData] = useState<T | null>(null)
  const [galat, setGalat] = useState('')
  const [memuat, setMemuat] = useState(true)
  const ambilRef = useRef(ambil)
  ambilRef.current = ambil
  const urutan = useRef(0)

  // `senyap` untuk penyegaran berkala: tanpa indikator memuat, dan kegagalannya membiarkan data terakhir.
  const muat = useCallback(async (senyap?: boolean) => {
    const nomor = ++urutan.current
    if (senyap !== true) setMemuat(true)
    try {
      const hasil = await ambilRef.current()
      if (nomor !== urutan.current) return
      // Data yang sama tidak diganti, supaya tampilan tidak digambar ulang.
      setData((lama) => (JSON.stringify(lama) === JSON.stringify(hasil) ? lama : hasil))
      setGalat('')
    } catch (error) {
      if (nomor === urutan.current && senyap !== true) setGalat(errorMessage(error))
    } finally {
      if (nomor === urutan.current) setMemuat(false)
    }
  }, [])

  useEffect(() => {
    setData(null)
    void muat()
    const segarkan = () => {
      if (document.visibilityState === 'visible') void muat(true)
    }
    const timer = setInterval(segarkan, jedaMs)
    document.addEventListener('visibilitychange', segarkan)
    return () => {
      clearInterval(timer)
      document.removeEventListener('visibilitychange', segarkan)
      urutan.current++
    }
  }, [kunci, jedaMs, muat])

  return { data, galat, memuat, muat }
}

export function TagKeadaan({ p }: { p: Submission }) {
  if (p.status === 'disetujui') return <Tag color="success">Disetujui</Tag>
  if (p.status === 'dibatalkan') return <Tag>Dibatalkan</Tag>
  if (p.status === 'ditolak') return <Tag color="error">Ditolak</Tag>
  if (p.pesan_galat) return <Tag color="error">Proses bermasalah</Tag>
  if (p.tahap === 'tinjau') return <Tag color="warning">Menunggu keputusan DPA</Tag>
  if (p.tahap === 'revisi') return <Tag color="processing">Sedang direvisi</Tag>
  if (p.tahap === 'periksa') return <Tag color="processing">Diperiksa mahasiswa</Tag>
  return <Tag color="processing">Diproses sistem</Tag>
}

export const waktu = (iso: string | null) => (iso ? new Date(iso).toLocaleString('id-ID', { dateStyle: 'medium', timeStyle: 'short' }) : '—')

export function lama(iso: string): string {
  const jam = Math.max(0, Math.floor((Date.now() - new Date(iso).getTime()) / 3_600_000))
  if (jam < 1) return 'kurang dari 1 jam'
  return jam < 24 ? `${jam} jam` : `${Math.floor(jam / 24)} hari`
}
