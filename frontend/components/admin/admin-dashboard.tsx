'use client'

import Link from 'next/link'
import {
  Alert,
  Card,
  Col,
  Empty,
  List,
  Row,
  Space,
  Spin,
  Statistic,
  Tag,
  Typography,
} from 'antd'
import {
  ApartmentOutlined,
  AuditOutlined,
  BookOutlined,
  KeyOutlined,
  SolutionOutlined,
  TeamOutlined,
  UserOutlined,
  UserSwitchOutlined,
  WarningOutlined,
} from '@ant-design/icons'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { adminService, type AdminRingkasan, type AuditEntry } from '@/src/services/admin-service'
import { useLoad, useOrang, useStruktur, waktu } from './ui'

const WARNA = ['#2858e8', '#0f9d8a', '#d97706', '#dc2626', '#64748b', '#7c3aed', '#0891b2']
const LABEL_PERAN: Record<string, string> = {
  mahasiswa: 'Mahasiswa',
  dosen_pa: 'Dosen PA',
  kaprodi: 'Kaprodi',
  kajur: 'Kajur',
  dekan: 'Dekan',
}
const LABEL_STATUS: Record<string, string> = {
  aktif: 'Aktif',
  cuti: 'Cuti',
  lulus: 'Lulus',
  keluar: 'Keluar',
  pindah: 'Pindah',
  diajukan: 'Diajukan',
  disetujui: 'Disetujui',
  ditolak: 'Ditolak',
  revisi: 'Revisi',
  dibatalkan: 'Dibatalkan',
  ditangguhkan: 'Ditangguhkan',
  nonaktif: 'Nonaktif',
}

type DashboardData = {
  ringkasan: AdminRingkasan
  audit: AuditEntry[]
}

function keSeries(map: Record<string, number>, labels: Record<string, string> = {}) {
  return Object.entries(map)
    .filter(([, total]) => total > 0)
    .map(([kunci, total]) => ({ kunci, nama: labels[kunci] ?? kunci, total }))
    .sort((a, b) => b.total - a.total)
}

function tipNilai({ active, payload }: { active?: boolean; payload?: { name?: string; value?: number; payload?: { nama?: string } }[] }) {
  if (!active || !payload?.length) return null
  const item = payload[0]
  return (
    <div className="admin-chart-tooltip">
      <strong>{item.payload?.nama ?? item.name}</strong>
      <span>{item.value?.toLocaleString('id-ID')}</span>
    </div>
  )
}

export function AdminDashboard() {
  const { isSuper } = useStruktur()
  const muat = useLoad(async (): Promise<DashboardData> => {
    const [ringkasan, audit] = await Promise.all([
      adminService.ringkasan(),
      isSuper
        ? adminService.daftarAudit({ ukuran: 8 }).then((r) => r.data).catch(() => [] as AuditEntry[])
        : Promise.resolve([] as AuditEntry[]),
    ])
    return { ringkasan, audit }
  }, [isSuper])

  const data = muat.data?.ringkasan
  const audit = muat.data?.audit ?? []
  const namaPelaku = useOrang(audit.map((a) => a.pelaku_id))

  const peranSeries = keSeries(data?.peran ?? {}, LABEL_PERAN)
  const keanggotaanSeries = keSeries(data?.keanggotaan_status ?? {}, LABEL_STATUS)
  const pengajuanSeries = keSeries(data?.pengajuan_status ?? {}, LABEL_STATUS)
  const akunSeries = [
    { kunci: 'dengan', nama: 'Punya akun', total: data?.akun.dengan_akun ?? 0 },
    { kunci: 'tanpa', nama: 'Belum punya akun', total: data?.akun.tanpa_akun ?? 0 },
  ].filter((x) => x.total > 0)
  const dpaSeries = [
    { kunci: 'dengan', nama: 'Punya DPA', total: Math.max(0, (data?.mahasiswa_aktif ?? 0) - (data?.mahasiswa_tanpa_dpa ?? 0)) },
    { kunci: 'tanpa', nama: 'Tanpa DPA', total: data?.mahasiswa_tanpa_dpa ?? 0 },
  ].filter((x) => x.total > 0)
  const prodiSeries = (data?.mahasiswa_per_prodi ?? []).slice(0, 8).map((p) => ({
    nama: p.kode || p.nama,
    total: p.total,
    lengkap: p.nama,
  }))

  const kpi = [
    { title: 'Fakultas aktif', value: data?.struktur.fakultas ?? '—', href: '/admin/struktur', icon: <ApartmentOutlined /> },
    { title: 'Jurusan aktif', value: data?.struktur.jurusan ?? '—', href: '/admin/struktur', icon: <ApartmentOutlined /> },
    { title: 'Program studi aktif', value: data?.struktur.prodi ?? '—', href: '/admin/struktur', icon: <ApartmentOutlined /> },
    { title: 'Mahasiswa aktif', value: data?.mahasiswa_aktif ?? '—', href: '/admin/struktur', icon: <TeamOutlined /> },
    { title: 'Dosen PA aktif', value: data?.dosen_pa_aktif ?? '—', href: '/admin/penugasan', icon: <UserSwitchOutlined /> },
    { title: 'DPA aktif', value: data?.bimbingan_aktif ?? '—', href: '/admin/dpa', icon: <SolutionOutlined /> },
    { title: 'Kaprodi aktif', value: data?.kaprodi_aktif ?? '—', href: '/admin/penugasan', icon: <UserOutlined /> },
    { title: 'Orang terdaftar', value: data?.orang ?? '—', href: '/admin/orang', icon: <TeamOutlined /> },
  ]

  return (
    <div className="admin-dashboard">
      <Typography.Paragraph type="secondary" className="admin-dashboard-lead">
        Ringkasan operasional akademik di cakupan peran Anda — KPI, kesehatan data, dan grafik agregat dari layanan identity.
      </Typography.Paragraph>

      {muat.error && (
        <Alert type="error" showIcon message="Ringkasan gagal dimuat" description={muat.error} style={{ marginBottom: 16 }} />
      )}

      <Spin spinning={muat.loading && !data}>
        <Row gutter={[16, 16]}>
          {kpi.map((item) => (
            <Col xs={24} sm={12} lg={6} key={item.title}>
              <Link href={item.href} className="admin-kpi-link">
                <Card size="small" hoverable className="admin-kpi-card">
                  <Statistic title={item.title} value={item.value} prefix={item.icon} />
                </Card>
              </Link>
            </Col>
          ))}
        </Row>

        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} lg={14}>
            <Card title="Kesehatan data" className="admin-panel-card">
              {!data ? (
                <Empty description="Memuat indikator…" />
              ) : (
                <Space direction="vertical" size={12} style={{ width: '100%' }}>
                  <HealthItem
                    ok={data.mahasiswa_tanpa_dpa === 0}
                    title={
                      data.mahasiswa_tanpa_dpa === 0
                        ? 'Semua mahasiswa aktif punya DPA'
                        : `${data.mahasiswa_tanpa_dpa} mahasiswa tanpa DPA`
                    }
                    detail="Hitungan pasti dari keanggotaan aktif yang belum punya relasi bimbingan."
                    href="/admin/dpa"
                    action="Kelola DPA"
                  />
                  <HealthItem
                    ok={data.prodi_tanpa_kaprodi.length === 0}
                    title={
                      data.prodi_tanpa_kaprodi.length === 0
                        ? 'Semua prodi aktif punya kaprodi'
                        : `${data.prodi_tanpa_kaprodi.length} prodi tanpa kaprodi`
                    }
                    detail={daftarNama(data.prodi_tanpa_kaprodi, 'Setiap program studi aktif sudah punya penugasan kaprodi.')}
                    href="/admin/penugasan"
                    action="Kelola penugasan"
                  />
                  <HealthItem
                    ok={data.prodi_tanpa_panduan.length === 0}
                    title={
                      data.prodi_tanpa_panduan.length === 0
                        ? 'Semua prodi aktif punya panduan'
                        : `${data.prodi_tanpa_panduan.length} prodi tanpa panduan aktif`
                    }
                    detail={daftarNama(data.prodi_tanpa_panduan, 'Rekomendasi mata kuliah membutuhkan panduan akademik aktif.')}
                    href="/admin/panduan"
                    action="Kelola panduan"
                  />
                  <HealthItem
                    ok={data.akun.tanpa_akun === 0 && data.akun.wajib_ganti_sandi === 0}
                    title={
                      data.akun.tanpa_akun === 0 && data.akun.wajib_ganti_sandi === 0
                        ? 'Akun siap dipakai'
                        : [
                            data.akun.tanpa_akun ? `${data.akun.tanpa_akun} tanpa akun` : null,
                            data.akun.wajib_ganti_sandi ? `${data.akun.wajib_ganti_sandi} wajib ganti sandi` : null,
                          ]
                            .filter(Boolean)
                            .join(' · ')
                    }
                    detail="Orang tanpa akun belum bisa login; wajib ganti sandi biasanya dari akun baru atau reset."
                    href="/admin/orang"
                    action="Kelola orang"
                  />
                </Space>
              )}
            </Card>
          </Col>

          <Col xs={24} lg={10}>
            <Card title="Cakupan DPA" className="admin-panel-card">
              {dpaSeries.length === 0 ? (
                <Empty description="Belum ada mahasiswa aktif." />
              ) : (
                <div className="admin-chart-box">
                  <ResponsiveContainer width="100%" height={240}>
                    <PieChart>
                      <Pie data={dpaSeries} dataKey="total" nameKey="nama" innerRadius={58} outerRadius={88} paddingAngle={2}>
                        {dpaSeries.map((entry) => (
                          <Cell key={entry.kunci} fill={entry.kunci === 'tanpa' ? '#dc2626' : '#0f9d8a'} />
                        ))}
                      </Pie>
                      <Tooltip content={tipNilai} />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                  <Typography.Text type="secondary" className="admin-chart-caption">
                    {data
                      ? `${Math.max(0, data.mahasiswa_aktif - data.mahasiswa_tanpa_dpa)} dari ${data.mahasiswa_aktif} mahasiswa sudah punya DPA`
                      : null}
                  </Typography.Text>
                </div>
              )}
            </Card>
          </Col>
        </Row>

        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} lg={12}>
            <Card title="Mahasiswa per program studi" className="admin-panel-card">
              {prodiSeries.length === 0 ? (
                <Empty description="Belum ada data mahasiswa per prodi." />
              ) : (
                <div className="admin-chart-box">
                  <ResponsiveContainer width="100%" height={280}>
                    <BarChart data={prodiSeries} margin={{ top: 8, right: 8, left: 0, bottom: 8 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e8edf5" />
                      <XAxis dataKey="nama" tick={{ fontSize: 12 }} interval={0} angle={prodiSeries.length > 5 ? -20 : 0} textAnchor={prodiSeries.length > 5 ? 'end' : 'middle'} height={prodiSeries.length > 5 ? 56 : 30} />
                      <YAxis allowDecimals={false} tick={{ fontSize: 12 }} width={36} />
                      <Tooltip
                        formatter={(value) => [Number(value).toLocaleString('id-ID'), 'Mahasiswa']}
                        labelFormatter={(_, items) => items?.[0]?.payload?.lengkap ?? ''}
                      />
                      <Bar dataKey="total" radius={[6, 6, 0, 0]} fill="#2858e8" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </Card>
          </Col>

          <Col xs={24} lg={12}>
            <Card title="Distribusi peran" className="admin-panel-card">
              {peranSeries.length === 0 ? (
                <Empty description="Belum ada data peran." />
              ) : (
                <div className="admin-chart-box">
                  <ResponsiveContainer width="100%" height={280}>
                    <PieChart>
                      <Pie data={peranSeries} dataKey="total" nameKey="nama" outerRadius={90} paddingAngle={1}>
                        {peranSeries.map((entry, i) => (
                          <Cell key={entry.kunci} fill={WARNA[i % WARNA.length]} />
                        ))}
                      </Pie>
                      <Tooltip content={tipNilai} />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              )}
            </Card>
          </Col>
        </Row>

        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} lg={8}>
            <Card title="Status keanggotaan" className="admin-panel-card">
              {keanggotaanSeries.length === 0 ? (
                <Empty description="Belum ada keanggotaan." />
              ) : (
                <div className="admin-chart-box">
                  <ResponsiveContainer width="100%" height={240}>
                    <BarChart data={keanggotaanSeries} layout="vertical" margin={{ top: 8, right: 12, left: 8, bottom: 8 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e8edf5" />
                      <XAxis type="number" allowDecimals={false} tick={{ fontSize: 12 }} />
                      <YAxis type="category" dataKey="nama" width={72} tick={{ fontSize: 12 }} />
                      <Tooltip content={tipNilai} />
                      <Bar dataKey="total" radius={[0, 6, 6, 0]}>
                        {keanggotaanSeries.map((entry, i) => (
                          <Cell key={entry.kunci} fill={WARNA[i % WARNA.length]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </Card>
          </Col>

          <Col xs={24} lg={8}>
            <Card title="Pengajuan rencana studi" className="admin-panel-card">
              {pengajuanSeries.length === 0 ? (
                <Empty description="Belum ada pengajuan." />
              ) : (
                <div className="admin-chart-box">
                  <ResponsiveContainer width="100%" height={240}>
                    <BarChart data={pengajuanSeries} margin={{ top: 8, right: 8, left: 0, bottom: 8 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e8edf5" />
                      <XAxis dataKey="nama" tick={{ fontSize: 11 }} interval={0} angle={-15} textAnchor="end" height={48} />
                      <YAxis allowDecimals={false} tick={{ fontSize: 12 }} width={32} />
                      <Tooltip content={tipNilai} />
                      <Bar dataKey="total" radius={[6, 6, 0, 0]}>
                        {pengajuanSeries.map((entry, i) => (
                          <Cell key={entry.kunci} fill={WARNA[i % WARNA.length]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </Card>
          </Col>

          <Col xs={24} lg={8}>
            <Card
              title="Akun login"
              className="admin-panel-card"
              extra={
                data ? (
                  <Tag icon={<KeyOutlined />} color={data.akun.wajib_ganti_sandi ? 'warning' : 'default'}>
                    {data.akun.wajib_ganti_sandi} wajib ganti sandi
                  </Tag>
                ) : null
              }
            >
              {akunSeries.length === 0 ? (
                <Empty description="Belum ada orang." />
              ) : (
                <div className="admin-chart-box">
                  <ResponsiveContainer width="100%" height={240}>
                    <PieChart>
                      <Pie data={akunSeries} dataKey="total" nameKey="nama" innerRadius={50} outerRadius={80}>
                        {akunSeries.map((entry) => (
                          <Cell key={entry.kunci} fill={entry.kunci === 'tanpa' ? '#d97706' : '#2858e8'} />
                        ))}
                      </Pie>
                      <Tooltip content={tipNilai} />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              )}
            </Card>
          </Col>
        </Row>

        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} lg={isSuper ? 14 : 24}>
            <Card title="Akses cepat" className="admin-panel-card">
              <Row gutter={[12, 12]}>
                {[
                  { href: '/admin/struktur', label: 'Struktur akademik', icon: <ApartmentOutlined />, desc: 'Fakultas, jurusan, dan prodi' },
                  { href: '/admin/orang', label: 'Orang & akun', icon: <TeamOutlined />, desc: 'Profil, akun, dan impor' },
                  { href: '/admin/penugasan', label: 'Penugasan', icon: <UserSwitchOutlined />, desc: 'Kaprodi, kajur, dosen PA' },
                  { href: '/admin/dpa', label: 'Bimbingan DPA', icon: <SolutionOutlined />, desc: 'Pasangkan mahasiswa–dosen' },
                  { href: '/admin/panduan', label: 'Panduan akademik', icon: <BookOutlined />, desc: 'Unggah dan aktifkan panduan' },
                  ...(isSuper
                    ? [{ href: '/admin/audit', label: 'Jejak audit', icon: <AuditOutlined />, desc: 'Riwayat perubahan data' }]
                    : []),
                ].map((item) => (
                  <Col xs={24} sm={12} key={item.href}>
                    <Link href={item.href} className="admin-quick-link">
                      <Card size="small" hoverable>
                        <Space align="start">
                          <span className="admin-quick-icon">{item.icon}</span>
                          <span>
                            <Typography.Text strong>{item.label}</Typography.Text>
                            <br />
                            <Typography.Text type="secondary">{item.desc}</Typography.Text>
                          </span>
                        </Space>
                      </Card>
                    </Link>
                  </Col>
                ))}
              </Row>
            </Card>
          </Col>

          {isSuper && (
            <Col xs={24} lg={10}>
              <Card title="Aktivitas terbaru" extra={<Link href="/admin/audit">Lihat semua</Link>} className="admin-panel-card">
                {audit.length === 0 ? (
                  <Empty description="Belum ada jejak audit." />
                ) : (
                  <List
                    size="small"
                    dataSource={audit}
                    renderItem={(item) => (
                      <List.Item className="admin-audit-item">
                        <List.Item.Meta
                          title={
                            <Space wrap size={6}>
                              <code>{item.aksi}</code>
                              <Tag>{item.objek_tipe}</Tag>
                            </Space>
                          }
                          description={
                            <Typography.Text type="secondary">
                              {waktu(item.waktu)} · {item.pelaku_id ? namaPelaku(item.pelaku_id) : 'sistem'}
                            </Typography.Text>
                          }
                        />
                      </List.Item>
                    )}
                  />
                )}
              </Card>
            </Col>
          )}
        </Row>
      </Spin>
    </div>
  )
}

function daftarNama(items: { nama: string }[], kosong: string) {
  if (!items.length) return kosong
  const tampil = items.slice(0, 4).map((p) => p.nama).join(', ')
  return items.length > 4 ? `${tampil} (+${items.length - 4})` : tampil
}

function HealthItem({
  ok,
  title,
  detail,
  href,
  action,
}: {
  ok: boolean
  title: string
  detail: string
  href: string
  action: string
}) {
  return (
    <Alert
      type={ok ? 'success' : 'warning'}
      showIcon
      icon={ok ? undefined : <WarningOutlined />}
      message={title}
      description={detail}
      action={
        !ok ? (
          <Link href={href}>
            <Typography.Link>{action}</Typography.Link>
          </Link>
        ) : undefined
      }
    />
  )
}
