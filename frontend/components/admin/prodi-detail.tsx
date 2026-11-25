'use client'

import Link from 'next/link'
import { Alert, Button, Card, Col, Descriptions, Empty, Result, Row, Space, Spin, Statistic, Tabs, Tag, Typography } from 'antd'
import { ApartmentOutlined, ArrowLeftOutlined, BookOutlined, TeamOutlined, UserSwitchOutlined } from '@ant-design/icons'
import { adminService } from '@/src/services/admin-service'
import { useLoad, useStruktur } from './ui'
import { TabBimbingan } from './tab-bimbingan'
import { TabPanduan } from './tab-panduan'
import { TabPenugasan } from './tab-penugasan'
import { TabMahasiswaProdi } from './tab-mahasiswa-prodi'

export function ProdiDetail({ prodiId }: { prodiId: string }) {
  const { unit, isSuper } = useStruktur()
  const detail = useLoad(() => adminService.ambilProdi(prodiId), [prodiId])
  const ringkasan = useLoad(async () => {
    const [orang, anggota, penugasan, panduan] = await Promise.all([
      adminService.daftarOrang({ prodi_id: prodiId, ukuran: 1 }),
      adminService.daftarKeanggotaan({ prodi_id: prodiId, aktif: true, ukuran: 1 }),
      adminService.daftarPenugasan({ unit_id: prodiId, aktif: true, ukuran: 200 }),
      adminService.daftarPanduan(prodiId),
    ])
    return {
      orang: orang.total,
      mahasiswa: anggota.total,
      dosenPa: penugasan.data.filter((item) => item.peran === 'dosen_pa').length,
      panduanAktif: panduan.data.find((item) => item.status === 'aktif') ?? null,
    }
  }, [prodiId])

  if (detail.loading || ringkasan.loading) return <div className="admin-loading"><Spin size="large" /></div>
  if (detail.error) return <Result status="error" title="Program studi tidak dapat dimuat" subTitle={detail.error} extra={<Button href="/admin/struktur">Kembali ke struktur</Button>} />
  if (!detail.data) return <Empty description="Program studi tidak ditemukan." />

  const info = unit.get(prodiId)
  const prodi = detail.data
  const stats = ringkasan.data
  return <div className="prodi-detail">
    <Card className="prodi-identity" variant="borderless">
      <Button type="link" href="/admin/struktur" icon={<ArrowLeftOutlined />} className="prodi-back">Struktur akademik</Button>
      <div className="prodi-identity-row">
        <div className="prodi-monogram" aria-hidden="true">{prodi.kode.slice(0, 2)}</div>
        <div className="prodi-identity-copy">
          <Space align="center" size={12} wrap><Typography.Title level={2}>{prodi.nama}</Typography.Title><Tag color={prodi.aktif ? 'success' : 'error'}>{prodi.aktif ? 'Aktif' : 'Nonaktif'}</Tag></Space>
          <Typography.Text type="secondary">{info?.jalur ?? 'Program studi'}</Typography.Text>
          <div className="prodi-meta"><Tag variant="filled">Kode {prodi.kode}</Tag><Tag variant="filled">{prodi.jenjang}</Tag></div>
        </div>
      </div>
    </Card>
    {!isSuper && <Alert type="info" showIcon message="Akses mengikuti cakupan peran Anda. Server tetap memeriksa izin pada setiap tindakan." />}
    <Row gutter={[0, 0]} className="prodi-statistics">
      <Col xs={12} md={6}><div className="prodi-metric"><Statistic title="Mahasiswa aktif" value={stats?.mahasiswa ?? 0} prefix={<TeamOutlined />} /></div></Col>
      <Col xs={12} md={6}><div className="prodi-metric"><Statistic title="Dosen PA" value={stats?.dosenPa ?? 0} prefix={<UserSwitchOutlined />} /></div></Col>
      <Col xs={12} md={6}><div className="prodi-metric"><Statistic title="Orang di prodi" value={stats?.orang ?? 0} prefix={<TeamOutlined />} /></div></Col>
      <Col xs={12} md={6}><div className="prodi-metric"><Statistic title="Batas SKS" value={prodi.maks_sks_semester ?? 24} suffix="SKS" prefix={<BookOutlined />} /></div></Col>
    </Row>
    <Card className="prodi-workspace" variant="borderless"><Tabs items={[
      { key: 'ringkasan', label: 'Ringkasan', icon: <ApartmentOutlined />, children: <Card size="small" title="Informasi program studi"><Descriptions column={{ xs: 1, sm: 2 }} items={[{ key: 'kode', label: 'Kode', children: prodi.kode }, { key: 'jenjang', label: 'Jenjang', children: prodi.jenjang }, { key: 'sks', label: 'Batas SKS per semester', children: `${prodi.maks_sks_semester ?? 24} SKS` }, { key: 'panduan', label: 'Panduan aktif', children: stats?.panduanAktif ? <Tag color="success">v{stats.panduanAktif.versi}</Tag> : <Tag color="warning">Belum ada</Tag> }]} /></Card> },
      { key: 'dosen', label: 'Dosen & penugasan', icon: <UserSwitchOutlined />, children: <TabPenugasan prodiId={prodiId} /> },
      { key: 'panduan', label: 'Panduan akademik', icon: <BookOutlined />, children: <TabPanduan initialProdiId={prodiId} /> },
      { key: 'mahasiswa', label: 'Mahasiswa', icon: <TeamOutlined />, children: <TabMahasiswaProdi prodiId={prodiId} /> },
      { key: 'dpa', label: 'DPA', icon: <UserSwitchOutlined />, children: <TabBimbingan prodiId={prodiId} /> },
    ]} /></Card>
  </div>
}
