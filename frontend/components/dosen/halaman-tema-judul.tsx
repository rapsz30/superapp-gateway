'use client'

import { useEffect, useMemo, useState } from 'react'
import { Alert, Button, Card, Empty, Flex, Select, Statistic, Table, Tag, Typography, Row, Col } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { BrandedLoading } from '@/components/brand'
import { errorMessage } from '@/src/lib/api'
import { judulStaffService, type ThesisThemeSummary } from '@/src/services/judul-staff-service'
import { useDosen } from './dosen-shell'

export function HalamanTemaJudul() {
  const dosen = useDosen()
  const options = useMemo(() => {
    const unique = new Map<string, { value: string; label: string }>()
    for (const unit of dosen.units) {
      if (unit.tipe === 'prodi' && unit.id && !unique.has(unit.id)) {
        unique.set(unit.id, { value: unit.id, label: unit.nama ?? unit.id })
      }
    }
    return Array.from(unique.values())
  }, [dosen.units])
  const [prodiId, setProdiId] = useState<string | undefined>(options.length === 1 ? options[0].value : undefined)
  const [data, setData] = useState<ThesisThemeSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  async function load() {
    setLoading(true)
    setError('')
    try {
      setData(await judulStaffService.statistikTema(prodiId))
    } catch (caught) {
      setError(errorMessage(caught, 'Statistik tema belum dapat dimuat.'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [prodiId])

  const rows = useMemo(() => data.flatMap((summary) => summary.tema.map((item) => ({ ...item, prodi: summary.prodi.nama, prodiId: summary.prodi.id }))), [data])
  const total = data.reduce((sum, summary) => sum + summary.total, 0)
  const approved = data.reduce((sum, summary) => sum + summary.tema.reduce((part, item) => part + item.disetujui, 0), 0)
  const top = rows[0]
  const chartData = rows.slice(0, 12).map((item) => ({ ...item, label: item.tema.length > 34 ? `${item.tema.slice(0, 31)}…` : item.tema }))

  return <Flex vertical gap={16}>
    {error && <Alert type="error" showIcon title={error} action={<Button size="small" onClick={() => void load()}>Coba lagi</Button>} />}
    <Card title={<div><Typography.Title level={4} style={{ margin: 0 }}>Tema judul</Typography.Title><Typography.Text type="secondary">Lihat tema tugas akhir yang paling banyak dipilih per program studi.</Typography.Text></div>} extra={<Button icon={<ReloadOutlined />} loading={loading} onClick={() => void load()}>Muat ulang</Button>}>
      {options.length > 0 && <Select aria-label="Program studi" allowClear value={prodiId} onChange={(value) => setProdiId(value)} placeholder="Semua program studi dalam cakupan" options={options} style={{ minWidth: 280, marginBottom: 18 }} />}
      {loading && !data.length ? <div className="analitik-muat"><BrandedLoading message="Memuat sebaran tema..." /></div> : !data.length ? <Empty description="Belum ada pengajuan judul di prodi ini." /> : <>
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={8}><Card size="small"><Statistic title="Total judul" value={total} /></Card></Col>
          <Col xs={24} sm={8}><Card size="small"><Statistic title="Disetujui" value={approved} /></Card></Col>
          <Col xs={24} sm={8}><Card size="small"><Statistic title="Tema teratas" value={top?.tema ?? '—'} styles={{ content: { fontSize: 18 } }} /></Card></Col>
        </Row>
        <Card size="small" title="Tema terbanyak" style={{ marginTop: 18 }}>
          <ResponsiveContainer width="100%" height={Math.max(300, chartData.length * 42)}>
            <BarChart data={chartData} layout="vertical" margin={{ top: 8, right: 24, left: 10, bottom: 8 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} />
              <XAxis type="number" allowDecimals={false} />
              <YAxis type="category" dataKey="label" width={190} tick={{ fontSize: 12 }} />
              <Tooltip />
              <Legend />
              <Bar dataKey="disetujui" name="Disetujui" stackId="tema" fill="#0f9d8a" />
              <Bar dataKey="berjalan" name="Berjalan" stackId="tema" fill="#2858e8" radius={[0, 5, 5, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
        <Table style={{ marginTop: 18 }} rowKey={(row) => `${row.prodiId}-${row.tema}`} dataSource={rows} pagination={false} scroll={{ x: 720 }} columns={[
          { title: 'Program studi', dataIndex: 'prodi', render: (value: string) => <Tag>{value}</Tag> },
          { title: 'Tema', dataIndex: 'tema' },
          { title: 'Disetujui', dataIndex: 'disetujui' },
          { title: 'Berjalan', dataIndex: 'berjalan' },
          { title: 'Total', dataIndex: 'total' },
          { title: 'Persentase', key: 'persentase', render: (_, row) => `${total ? Math.round(row.total / total * 100) : 0}%` },
        ]} />
      </>}
    </Card>
  </Flex>
}
