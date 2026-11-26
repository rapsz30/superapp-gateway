'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Alert, App, Button, Card, Descriptions, Flex, Input, Spin, Tag, Typography } from 'antd'
import { ArrowLeftOutlined, CheckOutlined, RollbackOutlined } from '@ant-design/icons'
import { errorMessage } from '@/src/lib/api'
import type { ThesisSubmission } from '@/src/services/judul-service'
import { judulStaffService } from '@/src/services/judul-staff-service'
import { useMuat, waktu } from './bersama'
import { useDosen } from './dosen-shell'

export function DetailJudulTa({ id }: { id: string }) {
  const dosen = useDosen()
  const router = useRouter()
  const { message, modal } = App.useApp()
  const { data: submission, galat, memuat, muat } = useMuat(id, () => judulStaffService.ambil(id), 10_000)
  const [catatan, setCatatan] = useState('')
  const [mengirim, setMengirim] = useState(false)

  if (!submission) return memuat ? <Spin size="large" /> : <Alert type="error" showIcon title={galat || 'Pengajuan tidak ditemukan.'} action={<Button onClick={() => router.back()}>Kembali</Button>} />

  const dapatDiputuskan = submission.pembimbing?.id === dosen.id && submission.status === 'diajukan' && submission.tahap === 'tinjau'
  async function putuskan(keputusan: 'setuju' | 'revisi') {
    if (keputusan === 'revisi' && !catatan.trim()) return
    setMengirim(true)
    try {
      await judulStaffService.putuskan(id, keputusan, catatan)
      message.success(keputusan === 'setuju' ? 'Judul disetujui.' : 'Catatan revisi dikirim ke mahasiswa.')
      await muat()
      setCatatan('')
    } catch (error) {
      message.error(errorMessage(error, 'Keputusan belum dapat disimpan. Muat ulang lalu coba lagi.'))
    } finally {
      setMengirim(false)
    }
  }

  function setujui() {
    modal.confirm({ title: 'Setujui judul ini?', content: 'Setelah disetujui, pengajuan tidak dapat diproses ulang dari halaman ini.', okText: 'Setujui', cancelText: 'Batal', onOk: () => putuskan('setuju') })
  }

  return <Flex vertical gap={16}>
    <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => router.back()}>Kembali ke antrean</Button>
    {galat && <Alert type="warning" showIcon title={galat} />}
    <Card title={<div><Typography.Title level={4} style={{ margin: 0 }}>{submission.judul}</Typography.Title><Tag color="blue">{submission.tema}</Tag></div>} extra={submission.status === 'disetujui' ? <Tag color="success">Disetujui</Tag> : <Tag color="processing">{submission.tahap === 'perbaikan' ? 'Menunggu perbaikan' : 'Menunggu tinjauan'}</Tag>}>
      <Descriptions column={{ xs: 1, md: 2 }} items={[
        { key: 'mahasiswa', label: 'Mahasiswa', children: submission.mahasiswa?.nama_lengkap ?? '—' },
        { key: 'nim', label: 'NIM', children: submission.mahasiswa?.nim ?? '—' },
        { key: 'prodi', label: 'Program studi', children: submission.prodi?.nama ?? '—' },
        { key: 'topik', label: 'Minat awal', children: submission.topik || '—' },
        { key: 'diajukan', label: 'Diajukan', children: waktu(submission.diajukan_pada) },
        { key: 'revisi', label: 'Revisi', children: `Ke-${submission.jumlah_revisi}` },
      ]} />
    </Card>
    <Card title="Detail penelitian">
      <Flex vertical gap={16}>
        <section><Typography.Text strong>Deskripsi</Typography.Text><Typography.Paragraph>{submission.deskripsi}</Typography.Paragraph></section>
        <section><Typography.Text strong>Metodologi</Typography.Text>{submission.metodologi ? <Typography.Paragraph style={{ whiteSpace: 'pre-line' }}>{submission.metodologi}</Typography.Paragraph> : <Typography.Text type="secondary">Belum diisi.</Typography.Text>}</section>
        <section><Typography.Text strong>Kata kunci</Typography.Text><div style={{ marginTop: 8 }}>{submission.keywords.length ? submission.keywords.map((keyword) => <Tag key={keyword}>{keyword}</Tag>) : <Typography.Text type="secondary">Belum diisi.</Typography.Text>}</div></section>
        <section><Typography.Text strong>Referensi</Typography.Text>{submission.referensi.length ? <div style={{ marginTop: 8 }}>{submission.referensi.map((ref) => <div key={ref.link} style={{ paddingBlock: 6 }}><a href={ref.link} target="_blank" rel="noopener noreferrer">{ref.sitasi}</a></div>)}</div> : <Typography.Text type="secondary">Belum diisi.</Typography.Text>}</section>
      </Flex>
    </Card>
    {submission.catatan && <Alert type="warning" showIcon title="Catatan sebelumnya" description={submission.catatan} />}
    {dapatDiputuskan && <Card title="Keputusan">
      <Flex vertical gap={12}><Input.TextArea value={catatan} onChange={(event) => setCatatan(event.target.value)} rows={4} maxLength={1000} showCount placeholder="Catatan wajib diisi bila meminta revisi." /><Flex gap={8} wrap><Button type="primary" icon={<CheckOutlined />} loading={mengirim} onClick={setujui}>Setujui judul</Button><Button icon={<RollbackOutlined />} loading={mengirim} disabled={!catatan.trim()} onClick={() => void putuskan('revisi')}>Minta revisi</Button></Flex></Flex>
    </Card>}
  </Flex>
}
