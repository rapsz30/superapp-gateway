'use client'
import Link from 'next/link'
import { Alert, Card, Flex, Table, Typography } from 'antd'
import { dosenService } from '@/src/services/dosen-service'
import { TagKeadaan, useMuat } from './bersama'
import { useDosen } from './dosen-shell'

export function HalamanBimbingan() {
  const dosen = useDosen()
  const { data, galat, memuat } = useMuat(dosen.id, async () => {
    const [bimbingan, pengajuan] = await Promise.all([
      dosenService.mahasiswaBimbingan(dosen.id),
      dosenService.pengajuanBimbingan(dosen.id),
    ])
    // Server mengurutkan pengajuan dari yang terbaru, jadi yang pertama ditemukan adalah yang terakhir diajukan.
    return bimbingan.map((b) => ({ ...b, terakhir: pengajuan.find((p) => p.mahasiswa?.id === b.bimbingan.mahasiswa_id) }))
  }, 60_000)

  return (
    <Flex vertical gap={16}>
      {galat && <Alert type="error" showIcon title={galat} />}
      <Card>
        <Table
          rowKey={(r) => r.bimbingan.id}
          dataSource={data ?? []}
          loading={memuat && !data}
          scroll={{ x: 'max-content' }}
          locale={{ emptyText: 'Belum ada mahasiswa bimbingan. Penugasan diatur oleh kaprodi.' }}
          pagination={{ pageSize: 20, hideOnSinglePage: true }}
          columns={[
            { title: 'Nama', key: 'nama', render: (_, r) => <Typography.Text strong>{r.mahasiswa?.nama_lengkap ?? '—'}</Typography.Text> },
            { title: 'NIM', key: 'nim', render: (_, r) => r.mahasiswa?.nim ?? '—' },
            { title: 'Dibimbing sejak', key: 'mulai', render: (_, r) => new Date(r.bimbingan.mulai).toLocaleDateString('id-ID', { dateStyle: 'medium' }) },
            { title: 'Pengajuan terakhir', key: 'pengajuan', render: (_, r) => (r.terakhir ? <Link href={`/dosen/pengajuan/${r.terakhir.id}`}><TagKeadaan p={r.terakhir} /></Link> : <Typography.Text type="secondary">Belum mengajukan</Typography.Text>) },
          ]}
        />
      </Card>
    </Flex>
  )
}
