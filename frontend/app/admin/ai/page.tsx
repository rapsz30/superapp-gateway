'use client'

import { useMemo, useState } from 'react'
import { Alert, Card, Col, DatePicker, Row, Space, Spin, Statistic, Table, Typography } from 'antd'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import dayjs, { type Dayjs } from 'dayjs'
import { adminService } from '@/src/services/admin-service'
import type { AiPemakaian } from '@/src/services/admin-service'
import { useLoad } from '@/components/admin/ui'

const angka = (n: number) => new Intl.NumberFormat('id-ID').format(n)
const { RangePicker } = DatePicker

export default function PemakaianAiPage() {
  const [rentang, setRentang] = useState<[Dayjs, Dayjs]>([dayjs().subtract(29, 'day'), dayjs()])
  const dari = rentang[0].format('YYYY-MM-DD')
  const sampai = rentang[1].format('YYYY-MM-DD')
  const data = useLoad(() => adminService.pemakaianAi({ dari, sampai }), [dari, sampai])
  const kolomFitur = useMemo(() => [
    { title: 'Layanan', dataIndex: 'layanan' }, { title: 'Fitur', dataIndex: 'fitur' }, { title: 'Model', dataIndex: 'model' },
    { title: 'Panggilan', dataIndex: 'panggilan', render: angka }, { title: 'Gagal', dataIndex: 'gagal', render: angka },
    { title: 'Token masuk', dataIndex: 'token_masuk', render: angka }, { title: 'Token keluar', dataIndex: 'token_keluar', render: angka },
    { title: 'Durasi rata-rata', dataIndex: 'rata_durasi_ms', render: (v: number) => `${angka(v)} ms` },
  ], [])
  const kolomPengguna = useMemo(() => [
    { title: 'Nama', dataIndex: 'nama', render: (v: string | null) => v || 'Tidak diketahui' },
    { title: 'Email', dataIndex: 'email', render: (v: string | null) => v || '—' },
    { title: 'Panggilan', dataIndex: 'panggilan', render: angka }, { title: 'Gagal', dataIndex: 'gagal', render: angka },
    { title: 'Token masuk', dataIndex: 'token_masuk', render: angka }, { title: 'Token keluar', dataIndex: 'token_keluar', render: angka },
  ], [])

  return <Space direction="vertical" size="large" style={{ width: '100%' }}>
    <Typography.Paragraph type="secondary">Angka mencakup pemakaian aplikasi ini sejak pencatatan dipasang.</Typography.Paragraph>
    <RangePicker value={rentang} onChange={(v) => { if (v?.[0] && v[1]) setRentang([v[0], v[1]]) }} allowClear={false} />
    {data.error && <Alert type="error" showIcon message={data.error} />}
    {data.loading && !data.data ? <Spin /> : data.data && <Isi data={data.data} kolomFitur={kolomFitur} kolomPengguna={kolomPengguna} />}
  </Space>
}

function Isi({ data, kolomFitur, kolomPengguna }: { data: AiPemakaian; kolomFitur: any[]; kolomPengguna: any[] }) {
  return <>
    <Row gutter={[16, 16]}>
      <Col xs={12} md={6}><Card><Statistic title="Panggilan" value={data.total.panggilan} formatter={(v) => angka(Number(v))} /></Card></Col>
      <Col xs={12} md={6}><Card><Statistic title="Gagal" value={data.total.gagal} formatter={(v) => angka(Number(v))} /></Card></Col>
      <Col xs={12} md={6}><Card><Statistic title="Token masuk" value={data.total.token_masuk} formatter={(v) => angka(Number(v))} /></Card></Col>
      <Col xs={12} md={6}><Card><Statistic title="Token keluar" value={data.total.token_keluar} formatter={(v) => angka(Number(v))} /></Card></Col>
      {data.harga && <Col xs={24} md={6}><Card><Statistic title="Perkiraan biaya" value={data.total.biaya_usd ?? 0} precision={4} prefix="$" /></Card></Col>}
    </Row>
    <Card title="Pemakaian harian"><div style={{ width: '100%', height: 280 }}><ResponsiveContainer><BarChart data={data.per_hari}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="tanggal" tickFormatter={(v) => String(v).slice(5)} /><YAxis /><Tooltip /><Bar dataKey="panggilan" fill="#1677ff" name="Panggilan" /><Bar dataKey="gagal" fill="#ff4d4f" name="Gagal" /></BarChart></ResponsiveContainer></div></Card>
    <Card title="Per fitur"><Table rowKey={(r) => `${r.layanan}-${r.fitur}-${r.model}`} dataSource={data.per_fitur} columns={kolomFitur} scroll={{ x: true }} pagination={{ pageSize: 10 }} /></Card>
    <Card title="Per pengguna"><Table rowKey={(r) => r.akun_id || 'unknown'} dataSource={data.per_pengguna} columns={kolomPengguna} scroll={{ x: true }} pagination={false} /></Card>
  </>
}
