'use client'
import Link from 'next/link'
import { Table, Typography, type TableColumnsType } from 'antd'
import type { Submission } from '@/src/services/pengajuan-service'
import { TagKeadaan, lama, waktu } from './bersama'

export function TabelPengajuan({ data, memuat, kosong, tampilDpa, final }: {
  data: Submission[]
  memuat: boolean
  kosong: string
  tampilDpa?: boolean
  /** Daftar riwayat: tampilkan waktu keputusan, bukan lama menunggu. */
  final?: boolean
}) {
  const kolom: TableColumnsType<Submission> = [
    {
      title: 'Mahasiswa',
      key: 'mahasiswa',
      render: (_, p) => (
        <>
          <Link href={`/dosen/pengajuan/${p.id}`}><Typography.Text strong>{p.mahasiswa?.nama_lengkap ?? '—'}</Typography.Text></Link>
          <br /><Typography.Text type="secondary">{p.mahasiswa?.nim ?? '—'}</Typography.Text>
        </>
      ),
    },
    { title: 'Semester tujuan', dataIndex: 'semester_target' },
    ...(tampilDpa ? [{ title: 'Pembimbing akademik', key: 'dpa', render: (_: unknown, p: Submission) => p.dpa?.nama_lengkap ?? '—' }] : []),
    { title: 'Keadaan', key: 'keadaan', render: (_, p) => <TagKeadaan p={p} /> },
    { title: 'Revisi', dataIndex: 'jumlah_revisi' },
    { title: 'Diajukan', key: 'diajukan', render: (_, p) => waktu(p.diajukan_pada) },
    final
      ? { title: 'Diputuskan', key: 'putus', render: (_, p) => waktu(p.diputuskan_pada) }
      : { title: 'Sejak diajukan', key: 'lama', render: (_, p) => (p.status === 'diajukan' ? lama(p.diajukan_pada) : '—') },
    { title: '', key: 'aksi', render: (_, p) => <Link href={`/dosen/pengajuan/${p.id}`}>{p.status === 'diajukan' && p.tahap === 'tinjau' && !tampilDpa ? 'Tinjau' : 'Lihat'}</Link> },
  ]
  return <Table rowKey="id" columns={kolom} dataSource={data} loading={memuat} scroll={{ x: 'max-content' }} locale={{ emptyText: kosong }} pagination={{ pageSize: 20, hideOnSinglePage: true }} />
}
