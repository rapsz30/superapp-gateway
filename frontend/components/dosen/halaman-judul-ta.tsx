'use client'

import Link from 'next/link'
import { Alert, Button, Card, Empty, Flex, Table, Tag, Typography, type TableColumnsType } from 'antd'
import { ClockCircleOutlined, FileDoneOutlined, ReloadOutlined } from '@ant-design/icons'
import type { ThesisSubmission } from '@/src/services/judul-service'
import { judulStaffService } from '@/src/services/judul-staff-service'
import { useMuat, waktu } from './bersama'
import { useDosen } from './dosen-shell'

function status(submission: ThesisSubmission) {
  if (submission.status === 'disetujui') return <Tag color="success">Disetujui</Tag>
  if (submission.status === 'dibatalkan') return <Tag>Dibatalkan</Tag>
  if (submission.tahap === 'perbaikan') return <Tag color="warning">Menunggu perbaikan</Tag>
  return <Tag color="processing">Menunggu tinjauan</Tag>
}

export function HalamanJudulTa({ riwayat = false }: { riwayat?: boolean }) {
  const dosen = useDosen()
  const { data, galat, memuat, muat } = useMuat(`judul-${dosen.id}`, () => judulStaffService.pengajuan(dosen.id), 20_000)
  const semua = data ?? []
  const menunggu = semua.filter((p) => p.status === 'diajukan' && p.tahap === 'tinjau')
  const selesai = semua.filter((p) => !(p.status === 'diajukan' && p.tahap === 'tinjau'))
  const tampil = riwayat ? selesai : menunggu
  const columns: TableColumnsType<ThesisSubmission> = [
    { title: 'Mahasiswa', key: 'mahasiswa', render: (_, p) => <div className="judul-ta-student"><Typography.Text strong>{p.mahasiswa?.nama_lengkap ?? '—'}</Typography.Text><Typography.Text type="secondary">NIM {p.mahasiswa?.nim ?? '—'}</Typography.Text></div> },
    { title: 'Tema', dataIndex: 'tema', render: (value: string) => <Tag color="blue">{value}</Tag> },
    { title: 'Judul', dataIndex: 'judul', render: (value: string, p) => <div><Typography.Text ellipsis={{ tooltip: value }} style={{ maxWidth: 340, display: 'inline-block' }}>{value}</Typography.Text>{p.jumlah_revisi > 0 && <><br /><Typography.Text type="secondary">Revisi ke-{p.jumlah_revisi}</Typography.Text></>}</div> },
    { title: riwayat ? 'Diajukan' : 'Menunggu sejak', key: 'waktu', render: (_, p) => waktu(p.diajukan_pada) },
    { title: 'Status', key: 'status', render: (_, p) => status(p) },
    { title: '', key: 'aksi', render: (_, p) => <Link className="judul-ta-action" href={`/dosen/judul/${p.id}`}>{riwayat ? 'Lihat detail' : 'Tinjau'} <span aria-hidden="true">→</span></Link> },
  ]
  const jumlah = tampil.length

  return <Flex vertical gap={18} className="judul-ta-page">
    {galat && <Alert type="error" showIcon title={galat} action={<Button size="small" onClick={() => void muat()}>Coba lagi</Button>} />}
    <div className="judul-ta-overview">
      <div className="judul-ta-overview-icon">{riwayat ? <FileDoneOutlined /> : <ClockCircleOutlined />}</div>
      <div className="judul-ta-overview-copy"><Typography.Text className="judul-ta-eyebrow">TUGAS AKHIR</Typography.Text><Typography.Title level={4}>{riwayat ? 'Arsip keputusan judul' : 'Antrean tinjauan judul'}</Typography.Title><Typography.Text type="secondary">{riwayat ? 'Telusuri pengajuan yang sudah melewati tahap tinjauan.' : 'Periksa usulan judul mahasiswa dan berikan keputusan.'}</Typography.Text></div>
      <div className="judul-ta-overview-count"><strong>{jumlah}</strong><span>{riwayat ? 'pengajuan selesai' : 'menunggu ditinjau'}</span></div>
    </div>
    <Card className="judul-ta-table-card" title={<div><Typography.Text strong>{riwayat ? 'Riwayat tugas akhir' : 'Pengajuan yang perlu ditinjau'}</Typography.Text><br /><Typography.Text type="secondary">{jumlah} pengajuan</Typography.Text></div>} extra={<Button icon={<ReloadOutlined />} loading={memuat} onClick={() => void muat()}>Muat ulang</Button>}>
      <Table rowKey="id" columns={columns} dataSource={tampil} loading={memuat && !data} scroll={{ x: 980 }} locale={{ emptyText: <Empty description={riwayat ? 'Belum ada pengajuan yang selesai ditinjau.' : 'Tidak ada judul yang menunggu keputusan Anda.'} /> }} pagination={{ pageSize: 10, hideOnSinglePage: true }} />
    </Card>
  </Flex>
}
