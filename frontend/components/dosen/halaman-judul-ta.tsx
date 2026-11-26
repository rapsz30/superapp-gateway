'use client'

import { useState } from 'react'

import Link from 'next/link'
import { Alert, Button, Card, Empty, Flex, Segmented, Table, Tag, Typography, type TableColumnsType } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import type { ThesisSubmission } from '@/src/services/judul-service'
import { judulStaffService } from '@/src/services/judul-staff-service'
import { useMuat, waktu } from './bersama'
import { useDosen } from './dosen-shell'

type Tab = 'menunggu' | 'riwayat'

function status(submission: ThesisSubmission) {
  if (submission.status === 'disetujui') return <Tag color="success">Disetujui</Tag>
  if (submission.status === 'dibatalkan') return <Tag>Dibatalkan</Tag>
  if (submission.tahap === 'perbaikan') return <Tag color="warning">Menunggu perbaikan</Tag>
  return <Tag color="processing">Menunggu tinjauan</Tag>
}

export function HalamanJudulTa() {
  const dosen = useDosen()
  const [tab, setTab] = useState<Tab>('menunggu')
  const { data, galat, memuat, muat } = useMuat(`judul-${dosen.id}`, () => judulStaffService.pengajuan(dosen.id), 20_000)
  const semua = data ?? []
  const menunggu = semua.filter((p) => p.status === 'diajukan' && p.tahap === 'tinjau')
  const riwayat = semua.filter((p) => !(p.status === 'diajukan' && p.tahap === 'tinjau'))
  const tampil = tab === 'menunggu' ? menunggu : riwayat
  const columns: TableColumnsType<ThesisSubmission> = [
    { title: 'Mahasiswa', key: 'mahasiswa', render: (_, p) => <div><Typography.Text strong>{p.mahasiswa?.nama_lengkap ?? '—'}</Typography.Text><br /><Typography.Text type="secondary">{p.mahasiswa?.nim ?? '—'}</Typography.Text></div> },
    { title: 'Tema', dataIndex: 'tema', render: (value: string) => <Tag color="blue">{value}</Tag> },
    { title: 'Judul', dataIndex: 'judul', render: (value: string, p) => <div><Typography.Text ellipsis={{ tooltip: value }} style={{ maxWidth: 340, display: 'inline-block' }}>{value}</Typography.Text>{p.jumlah_revisi > 0 && <><br /><Typography.Text type="secondary">Revisi ke-{p.jumlah_revisi}</Typography.Text></>}</div> },
    { title: tab === 'menunggu' ? 'Menunggu sejak' : 'Diajukan', key: 'waktu', render: (_, p) => waktu(p.diajukan_pada) },
    { title: 'Status', key: 'status', render: (_, p) => status(p) },
    { title: '', key: 'aksi', render: (_, p) => <Link href={`/dosen/judul/${p.id}`}>{tab === 'menunggu' ? 'Tinjau' : 'Lihat'}</Link> },
  ]

  return <Flex vertical gap={16}>
    {galat && <Alert type="error" showIcon title={galat} action={<Button size="small" onClick={() => void muat()}>Coba lagi</Button>} />}
    <Card title={<div><Typography.Title level={4} style={{ margin: 0 }}>Judul tugas akhir</Typography.Title><Typography.Text type="secondary">Kelola pengajuan yang ditujukan kepada Anda.</Typography.Text></div>} extra={<Button icon={<ReloadOutlined />} loading={memuat} onClick={() => void muat()}>Muat ulang</Button>}>
      <Segmented value={tab} onChange={(value) => setTab(value as Tab)} options={[{ value: 'menunggu', label: `Perlu ditinjau (${menunggu.length})` }, { value: 'riwayat', label: `Riwayat (${riwayat.length})` }]} />
      <Table style={{ marginTop: 18 }} rowKey="id" columns={columns} dataSource={tampil} loading={memuat && !data} scroll={{ x: 980 }} locale={{ emptyText: <Empty description={tab === 'menunggu' ? 'Tidak ada judul yang menunggu keputusan Anda.' : 'Belum ada riwayat pengajuan.'} /> }} pagination={{ pageSize: 10, hideOnSinglePage: true }} />
    </Card>
  </Flex>
}

