'use client'

import { useEffect, useMemo, useState } from 'react'
import { Alert, App, Button, Card, Empty, Flex, Select, Space, Switch, Table, Tag, Typography, type TableColumnsType } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import { errorMessage } from '@/src/lib/api'
import type { ThesisAssignmentRow, ThesisAdvisorCandidate } from '@/src/services/judul-staff-service'
import { judulStaffService } from '@/src/services/judul-staff-service'
import { useDosen } from './dosen-shell'

export function HalamanPembimbingTa() {
  const dosen = useDosen()
  const { modal, message } = App.useApp()
  const prodi = dosen.units.filter((unit) => unit.peran === 'kaprodi' && unit.tipe === 'prodi' && unit.id)
  const [prodiId, setProdiId] = useState(prodi[0]?.id ?? '')
  const [rows, setRows] = useState<ThesisAssignmentRow[]>([])
  const [candidates, setCandidates] = useState<ThesisAdvisorCandidate[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [onlyUnassigned, setOnlyUnassigned] = useState(false)

  async function load() {
    if (!prodiId) { setRows([]); setCandidates([]); setLoading(false); return }
    setLoading(true)
    setError('')
    try {
      const [assignment, advisor] = await Promise.all([judulStaffService.daftarMahasiswa(prodiId), judulStaffService.daftarPembimbing(prodiId)])
      setRows(assignment)
      setCandidates(advisor)
    } catch (caught) {
      setError(errorMessage(caught, 'Data pembimbing TA belum dapat dimuat.'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [prodiId])

  async function assign(row: ThesisAssignmentRow, dosenId: string) {
    const selected = candidates.find((candidate) => candidate.id === dosenId)
    if (!selected || selected.id === row.pembimbing?.id) return
    const sedangBerjalan = row.judul?.status === 'diajukan'
    modal.confirm({
      title: row.pembimbing ? 'Ganti pembimbing TA?' : 'Tunjuk pembimbing TA?',
      content: sedangBerjalan ? `Pengajuan judul ${row.mahasiswa.nama_lengkap} sedang berjalan. Antrean tinjauan akan ikut berpindah ke ${selected.nama_lengkap}.` : `Mahasiswa akan dibimbing oleh ${selected.nama_lengkap}.`,
      okText: row.pembimbing ? 'Ganti pembimbing' : 'Tunjuk pembimbing',
      cancelText: 'Batal',
      onOk: async () => {
        setSaving(row.mahasiswa.id)
        try {
          await judulStaffService.tunjukPembimbing(row.mahasiswa.id, dosenId)
          message.success('Pembimbing TA berhasil diperbarui.')
          await load()
        } catch (caught) {
          message.error(errorMessage(caught, 'Pembimbing belum dapat diperbarui.'))
        } finally {
          setSaving(null)
        }
      },
    })
  }

  const tampil = useMemo(() => onlyUnassigned ? rows.filter((row) => !row.pembimbing) : rows, [onlyUnassigned, rows])
  const columns: TableColumnsType<ThesisAssignmentRow> = [
    { title: 'Mahasiswa', key: 'mahasiswa', render: (_, row) => <div><Typography.Text strong>{row.mahasiswa.nama_lengkap}</Typography.Text><br /><Typography.Text type="secondary">{row.mahasiswa.nim ?? '—'}</Typography.Text></div> },
    { title: 'Pembimbing TA', key: 'pembimbing', render: (_, row) => row.pembimbing ? <Tag color="blue">{row.pembimbing.nama_lengkap}</Tag> : <Tag color="warning">Belum ditunjuk</Tag> },
    { title: 'Judul terakhir', key: 'judul', render: (_, row) => row.judul ? <div><Typography.Text ellipsis={{ tooltip: row.judul.judul }} style={{ maxWidth: 300, display: 'inline-block' }}>{row.judul.judul}</Typography.Text><br /><Tag>{row.judul.tema}</Tag></div> : <Typography.Text type="secondary">Belum ada pengajuan</Typography.Text> },
    { title: 'Status', key: 'status', render: (_, row) => row.judul ? <Tag color={row.judul.status === 'disetujui' ? 'success' : 'processing'}>{row.judul.status === 'disetujui' ? 'Disetujui' : row.judul.tahap === 'perbaikan' ? 'Perbaikan' : 'Berjalan'}</Tag> : '—' },
    { title: 'Aksi', key: 'aksi', render: (_, row) => <Select aria-label={`Pembimbing ${row.mahasiswa.nama_lengkap}`} value={row.pembimbing?.id} placeholder="Pilih dosen" loading={saving === row.mahasiswa.id} options={candidates.map((candidate) => ({ value: candidate.id, label: candidate.nama_lengkap }))} onChange={(value) => void assign(row, value)} style={{ minWidth: 190 }} /> },
  ]

  if (!prodi.length) return <Empty description="Anda belum ditugaskan sebagai kaprodi pada program studi mana pun." />
  return <Flex vertical gap={16}>
    {error && <Alert type="error" showIcon title={error} action={<Button size="small" onClick={() => void load()}>Coba lagi</Button>} />}
    <Card title={<div><Typography.Title level={4} style={{ margin: 0 }}>Pembimbing tugas akhir</Typography.Title><Typography.Text type="secondary">Tunjuk pembimbing TA per mahasiswa. Dosen dapat membimbing lintas prodi sesuai cakupannya.</Typography.Text></div>} extra={<Button icon={<ReloadOutlined />} loading={loading} onClick={() => void load()}>Muat ulang</Button>}>
      <Space wrap style={{ marginBottom: 18 }}>
        <Select aria-label="Program studi" value={prodiId} onChange={setProdiId} options={prodi.map((unit) => ({ value: unit.id!, label: unit.nama ?? unit.id! }))} style={{ minWidth: 240 }} />
        <Switch checked={onlyUnassigned} onChange={setOnlyUnassigned} />
        <Typography.Text>Hanya yang belum punya pembimbing</Typography.Text>
      </Space>
      <Table rowKey={(row) => row.mahasiswa.id} columns={columns} dataSource={tampil} loading={loading} scroll={{ x: 1050 }} locale={{ emptyText: <Empty description={onlyUnassigned ? 'Semua mahasiswa sudah memiliki pembimbing.' : 'Belum ada mahasiswa aktif di prodi ini.'} /> }} pagination={{ pageSize: 15, hideOnSinglePage: true }} />
    </Card>
  </Flex>
}
