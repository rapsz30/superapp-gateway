'use client'
import { Alert, Button, Card, Flex } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import { dosenService } from '@/src/services/dosen-service'
import { useMuat } from './bersama'
import { useDosen } from './dosen-shell'
import { TabelPengajuan } from './tabel-pengajuan'

export function HalamanTinjau() {
  const dosen = useDosen()
  const { data, galat, memuat, muat } = useMuat(dosen.id, () => dosenService.pengajuanBimbingan(dosen.id))
  const terbuka = (data ?? []).filter((p) => p.status === 'diajukan')
  const menunggu = terbuka.filter((p) => p.tahap === 'tinjau').sort((a, b) => a.diajukan_pada.localeCompare(b.diajukan_pada))
  const diproses = terbuka.filter((p) => p.tahap !== 'tinjau')
  const awal = memuat && !data

  return (
    <Flex vertical gap={16}>
      {galat && <Alert type="error" showIcon title={galat} />}
      <Card title={`Menunggu Anda (${menunggu.length})`} extra={<Button icon={<ReloadOutlined />} loading={memuat} onClick={() => void muat()}>Muat ulang</Button>}>
        <TabelPengajuan data={menunggu} memuat={awal} kosong="Tidak ada pengajuan yang menunggu keputusan Anda." />
      </Card>
      {diproses.length > 0 && (
        <Card title="Belum sampai ke Anda">
          <TabelPengajuan data={diproses} memuat={false} kosong="" />
        </Card>
      )}
    </Flex>
  )
}
