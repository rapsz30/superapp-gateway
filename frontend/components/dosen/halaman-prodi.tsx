'use client'
import { useState } from 'react'
import { Alert, Card, Col, Empty, Flex, Row, Segmented, Select, Statistic } from 'antd'
import { dosenService } from '@/src/services/dosen-service'
import { useMuat } from './bersama'
import { useDosen } from './dosen-shell'
import { TabelPengajuan } from './tabel-pengajuan'

type Saring = 'terbuka' | 'disetujui' | 'semua'

/** Pemantauan kaprodi. Proses tidak memiliki tugas untuk kaprodi, jadi halaman ini hanya membaca. */
export function HalamanProdi() {
  const dosen = useDosen()
  const prodi = dosen.units.filter((u) => u.peran === 'kaprodi' && u.tipe === 'prodi' && u.id)
  const [dipilih, setDipilih] = useState(prodi[0]?.id ?? '')
  const [saring, setSaring] = useState<Saring>('terbuka')
  const { data, galat, memuat } = useMuat(dipilih, () => (dipilih ? dosenService.pengajuanProdi(dipilih) : Promise.resolve([])), 30_000)

  if (!dipilih) return <Empty description="Anda belum ditugaskan sebagai kaprodi pada program studi mana pun." />

  const semua = data ?? []
  const terbuka = semua.filter((p) => p.status === 'diajukan')
  const tampil = saring === 'semua' ? semua : saring === 'terbuka' ? terbuka : semua.filter((p) => p.status === 'disetujui')
  const angka = [
    { judul: 'Sedang berjalan', nilai: terbuka.length },
    { judul: 'Menunggu keputusan DPA', nilai: terbuka.filter((p) => p.tahap === 'tinjau').length },
    { judul: 'Disetujui', nilai: semua.filter((p) => p.status === 'disetujui').length },
  ]

  return (
    <Flex vertical gap={16}>
      {galat && <Alert type="error" showIcon title={galat} />}
      <Select aria-label="Program studi" value={dipilih} onChange={setDipilih} style={{ maxWidth: 360, width: '100%' }} options={prodi.map((u) => ({ value: u.id!, label: u.nama ?? u.id! }))} />
      <Row gutter={[16, 16]}>
        {angka.map((a) => <Col xs={24} sm={8} key={a.judul}><Card><Statistic title={a.judul} value={a.nilai} loading={memuat && !data} /></Card></Col>)}
      </Row>
      <Card title="Pengajuan rencana studi" extra={<Segmented<Saring> value={saring} onChange={setSaring} options={[{ value: 'terbuka', label: 'Berjalan' }, { value: 'disetujui', label: 'Disetujui' }, { value: 'semua', label: 'Semua' }]} />}>
        <TabelPengajuan data={tampil} memuat={memuat && !data} kosong="Tidak ada pengajuan." tampilDpa />
      </Card>
    </Flex>
  )
}
