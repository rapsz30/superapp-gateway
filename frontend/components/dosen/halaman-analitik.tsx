'use client'
import { ReloadOutlined } from '@ant-design/icons'
import { Alert, Button, Card, Empty, Flex, Statistic, Table, Tabs, Typography } from 'antd'
import { useState } from 'react'
import { Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { BrandedLoading } from '@/components/brand'
import { waktu, useMuat } from './bersama'
import { analitikService, type DashboardCard, type TabAnalitik } from '@/src/services/analitik-service'

const WARNA = ['#2563eb', '#059669', '#d97706', '#7c3aed', '#e11d48', '#0891b2', '#ea580c', '#65a30d']

const TAB: { key: TabAnalitik; label: string }[] = [
  { key: 'ringkasan', label: 'Ringkasan' },
  { key: 'matkul', label: 'Mata Kuliah' },
  { key: 'judul', label: 'Judul Tugas Akhir' },
]

export function HalamanAnalitik() {
  const [tab, setTab] = useState<TabAnalitik>('ringkasan')
  return (
    <>
      <Tabs activeKey={tab} onChange={(kunci) => setTab(kunci as TabAnalitik)} items={TAB} />
      <IsiDashboard key={tab} tab={tab} />
    </>
  )
}

/**
 * Cerminan dashboard Analytics AlurKerja: judul, susunan, dan angka diambil saat halaman dimuat, jadi perubahan di
 * Studio ikut tampil. Jenis visual yang belum dikenal ditampilkan sebagai tabel.
 */
function IsiDashboard({ tab }: { tab: TabAnalitik }) {
  const { data, galat, memuat, muat } = useMuat(`analitik-${tab}`, () => analitikService.dashboard(tab), 60_000)

  if (!data) return galat ? <Alert type="error" showIcon title={galat} action={<Button size="small" onClick={() => void muat()}>Coba lagi</Button>} /> : <div className="analitik-muat"><BrandedLoading message="Memuat analitik..." /></div>

  return (
    <Flex vertical gap={16}>
      <Flex justify="space-between" align="flex-start" gap={12} wrap>
        <div>
          <Typography.Title level={4} style={{ margin: 0 }}>{data.judul}</Typography.Title>
          <Typography.Text type="secondary">{data.deskripsi}</Typography.Text><br />
          <Typography.Text type="secondary">Sumber: Analytics AlurKerja, rekap seluruh program studi. Diambil {waktu(data.diambil_pada)}.</Typography.Text>
        </div>
        <Button icon={<ReloadOutlined />} loading={memuat} onClick={() => void muat()}>Muat ulang</Button>
      </Flex>
      {galat && <Alert type="warning" showIcon title={`Data terakhir masih ditampilkan. ${galat}`} />}
      {data.kartu.length === 0 ? <Empty description="Dashboard ini belum memiliki kartu." /> : (
        <div className="analitik-kisi">
          {data.kartu.map((kartu) => (
            <Card key={kartu.id} size="small" title={kartu.judul || 'Kartu'} style={{ gridColumn: `${kartu.x + 1} / span ${kartu.w}` }}>
              <Isi kartu={kartu} />
            </Card>
          ))}
        </div>
      )}
    </Flex>
  )
}

function Isi({ kartu }: { kartu: DashboardCard }) {
  const { konfigurasi: k, baris, jenis } = kartu
  if (kartu.galat) return <Alert type="warning" showIcon title={kartu.galat} />
  if (baris.length === 0) return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Belum ada data." />
  const kolom = Object.keys(baris[0])

  if (jenis === 'number') {
    const nama = k.value_column && kolom.includes(k.value_column) ? k.value_column : kolom[0]
    const nilai = baris.reduce((jumlah, b) => jumlah + (Number(b[nama]) || 0), 0)
    return <Flex justify="center"><Statistic title={k.header || nama} value={baris.every((b) => b[nama] === null) ? '—' : nilai} decimalSeparator="," groupSeparator="." /></Flex>
  }

  const sumbuX = k.x_axis && kolom.includes(k.x_axis) ? k.x_axis : kolom[0]
  const seri = (k.y_axis ?? []).filter((nama) => kolom.includes(nama))
  if ((jenis === 'bar' || jenis === 'line') && seri.length > 0) {
    const warna = k.colors?.length ? k.colors : WARNA
    const data = baris.map((b) => ({ ...Object.fromEntries(seri.map((nama) => [nama, Number(b[nama]) || 0])), [sumbuX]: String(b[sumbuX] ?? '') }))
    const sumbu = <><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey={sumbuX} tick={{ fontSize: 12 }} /><YAxis allowDecimals={false} width={34} tick={{ fontSize: 12 }} /><Tooltip />{k.legend !== false && <Legend />}</>
    return (
      <ResponsiveContainer width="100%" height={260}>
        {jenis === 'line'
          ? <LineChart data={data}>{sumbu}{seri.map((nama, i) => <Line key={nama} isAnimationActive={false} dataKey={nama} stroke={warna[i % warna.length]} />)}</LineChart>
          : <BarChart data={data}>{sumbu}{seri.map((nama, i) => <Bar key={nama} isAnimationActive={false} dataKey={nama} fill={warna[i % warna.length]}>
            {seri.length === 1 && data.map((_, posisi) => <Cell key={posisi} fill={warna[posisi % warna.length]} />)}
          </Bar>)}</BarChart>}
      </ResponsiveContainer>
    )
  }

  return <Table size="small" scroll={{ x: true }} pagination={baris.length > 10 ? { pageSize: 10 } : false}
    rowKey="_kunci" dataSource={baris.map((b, i) => ({ ...b, _kunci: i }))}
    columns={kolom.map((nama) => ({ title: nama, dataIndex: nama, render: (v: unknown) => (v === null || v === undefined ? '—' : String(v)) }))} />
}
