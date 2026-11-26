'use client'
import { Alert, Card, Flex } from 'antd'
import { dosenService } from '@/src/services/dosen-service'
import { useMuat } from './bersama'
import { useDosen } from './dosen-shell'
import { TabelPengajuan } from './tabel-pengajuan'

export function HalamanRiwayat() {
  const dosen = useDosen()
  const { data, galat, memuat } = useMuat(dosen.id, () => dosenService.pengajuanBimbingan(dosen.id), 60_000)
  const selesai = (data ?? []).filter((p) => p.status !== 'diajukan')
  return (
    <Flex vertical gap={16}>
      {galat && <Alert type="error" showIcon title={galat} />}
      <Card><TabelPengajuan data={selesai} memuat={memuat && !data} kosong="Belum ada pengajuan yang selesai." final /></Card>
    </Flex>
  )
}
