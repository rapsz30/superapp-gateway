'use client'

import { useState } from 'react'
import { Button, Form, Input, InputNumber, Modal, Space, Table, Tag } from 'antd'
import type { Keanggotaan } from '@/src/services/admin-service'
import { adminService } from '@/src/services/admin-service'
import { errorMessage } from '@/src/lib/api'
import { FormMahasiswa } from './tab-bimbingan'
import { Kartu, Notice, SandiSementara, tanggal, useLoad, useOrang, useOrangData, useStruktur } from './ui'

const UKURAN = 20

function amankanCsv(nilai: string): string {
  const v = nilai.replace(/"/g, '""')
  if (/^[=+\-@]/.test(v)) return `"'${v}"`
  return `"${v}"`
}

export function TabMahasiswaProdi({ prodiId, terbuka = false }: { prodiId: string; terbuka?: boolean }) {
  const { isSuper } = useStruktur()
  const [halaman, setHalaman] = useState(1)
  const [tambahBuka, setTambahBuka] = useState(false)
  const [dummyBuka, setDummyBuka] = useState(false)
  const [dummyHasil, setDummyHasil] = useState<{ nama: string; email: string }[] | null>(null)
  const [dummyBusy, setDummyBusy] = useState(false)
  const [dummyError, setDummyError] = useState('')
  const [rahasia, setRahasia] = useState<{ email: string; sandi: string } | null>(null)

  const daftar = useLoad(
    () => adminService.daftarKeanggotaan({ prodi_id: prodiId, halaman, ukuran: UKURAN }),
    [prodiId, halaman],
  )
  const ids = (daftar.data?.data ?? []).map((item) => item.orang_id)
  const nama = useOrang(ids)
  const orang = useOrangData(ids)
  const rows = daftar.data?.data ?? []
  const total = daftar.data?.total ?? 0

  async function buatDummy(values: { jumlah: number; sandi: string; konfirmasi: string }) {
    if (values.sandi !== values.konfirmasi) {
      setDummyError('Konfirmasi sandi tidak cocok.')
      return
    }
    if (dummyBusy) return
    setDummyBusy(true)
    setDummyError('')
    try {
      const hasil = await adminService.buatMahasiswaDummy(prodiId, { jumlah: values.jumlah, sandi: values.sandi })
      setDummyHasil(hasil.akun)
      setDummyBuka(false)
      void daftar.reload()
    } catch (e) {
      setDummyError(errorMessage(e, 'Gagal membuat mahasiswa dummy.'))
    } finally {
      setDummyBusy(false)
    }
  }

  function unduhCsv() {
    if (!dummyHasil?.length) return
    const baris = ['nama,email', ...dummyHasil.map((a) => `${amankanCsv(a.nama)},${amankanCsv(a.email)}`)]
    const blob = new Blob([baris.join('\n')], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `mahasiswa-dummy-${prodiId.slice(0, 8)}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  const aksi = isSuper ? (
    <Space wrap>
      {terbuka && <Button onClick={() => { setDummyError(''); setDummyBuka(true) }}>Buat mahasiswa dummy</Button>}
      <Button type="primary" onClick={() => setTambahBuka(true)}>+ Tambah mahasiswa</Button>
    </Space>
  ) : undefined

  return (
    <Kartu judul="Mahasiswa program studi" aksi={aksi}>
      <p className="adm-muted">
        {terbuka
          ? 'Prodi terbuka: mahasiswa registrasi publik dan batch dummy otomatis tertaut ke dosen PA/kaprodi.'
          : 'Daftar mahasiswa yang terdaftar di program studi ini. Pembuatan akun bersifat opsional dan dapat dilakukan dari menu Orang & akun.'}
      </p>
      {daftar.error && <Notice tone="error">{daftar.error}</Notice>}
      {dummyHasil && (
        <div className="adm-stack" style={{ marginBottom: 16 }}>
          <Notice tone="ok">Berhasil membuat {dummyHasil.length} akun dummy.</Notice>
          <Table
            rowKey="email"
            size="small"
            dataSource={dummyHasil}
            pagination={{ pageSize: 10 }}
            columns={[
              { title: 'Nama', dataIndex: 'nama' },
              { title: 'Email', dataIndex: 'email' },
            ]}
          />
          <Button onClick={unduhCsv}>Unduh CSV</Button>
        </div>
      )}
      <Table<Keanggotaan>
        rowKey="id"
        loading={daftar.loading}
        dataSource={rows}
        pagination={{
          current: halaman,
          pageSize: UKURAN,
          total,
          showSizeChanger: false,
          showTotal: (t) => `${t} mahasiswa`,
          onChange: (h) => setHalaman(h),
        }}
        scroll={{ x: 900 }}
        locale={{ emptyText: 'Belum ada mahasiswa terdaftar.' }}
        columns={[
          { title: 'Nama mahasiswa', key: 'nama', render: (_, row) => nama(row.orang_id) },
          { title: 'Program studi (isian)', key: 'prodi_isian', render: (_, row) => orang(row.orang_id)?.prodi_isian ?? '—' },
          { title: 'Perguruan tinggi', key: 'pt_isian', render: (_, row) => orang(row.orang_id)?.pt_isian ?? '—' },
          { title: 'Angkatan', dataIndex: 'angkatan', render: (value: number | null) => value ?? '—' },
          { title: 'Status', dataIndex: 'status', render: (value: string, row) => <Tag color={row.selesai ? 'default' : value === 'aktif' ? 'success' : 'warning'}>{row.selesai ? 'Selesai' : value}</Tag> },
          { title: 'Mulai', dataIndex: 'mulai', render: (value: string) => tanggal(value) },
          { title: 'Selesai', dataIndex: 'selesai', render: (value: string | null) => tanggal(value) },
        ]}
      />
      <Modal open={tambahBuka} title="Tambah mahasiswa ke program studi" footer={null} onCancel={() => setTambahBuka(false)}>
        <FormMahasiswa prodiId={prodiId} onSelesai={(secret) => { setTambahBuka(false); if (secret) setRahasia(secret); void daftar.reload() }} />
      </Modal>
      <Modal open={dummyBuka} title="Buat mahasiswa dummy" footer={null} onCancel={() => !dummyBusy && setDummyBuka(false)} destroyOnHidden>
        <Form layout="vertical" onFinish={(v) => void buatDummy(v)} disabled={dummyBusy}>
          <Form.Item name="jumlah" label="Jumlah" rules={[{ required: true }]} initialValue={10}>
            <InputNumber min={1} max={300} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="sandi" label="Sandi bersama" rules={[{ required: true, min: 10 }]}>
            <Input.Password />
          </Form.Item>
          <Form.Item name="konfirmasi" label="Konfirmasi sandi" rules={[{ required: true }]}>
            <Input.Password />
          </Form.Item>
          {dummyError && <Notice tone="error">{dummyError}</Notice>}
          <Button type="primary" htmlType="submit" loading={dummyBusy} block>
            Buat akun
          </Button>
        </Form>
      </Modal>
      {rahasia && <Modal open title="Sandi sementara mahasiswa" footer={null} closable={false} maskClosable={false} keyboard={false}><SandiSementara {...rahasia} onClose={() => setRahasia(null)} /></Modal>}
    </Kartu>
  )
}
