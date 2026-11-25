'use client'

import { useState } from 'react'
import { Button, Modal, Table, Tag } from 'antd'
import type { Keanggotaan } from '@/src/services/admin-service'
import { adminService } from '@/src/services/admin-service'
import { FormMahasiswa } from './tab-bimbingan'
import { Badge, Kartu, Notice, SandiSementara, tanggal, useLoad, useOrang, useStruktur } from './ui'

export function TabMahasiswaProdi({ prodiId }: { prodiId: string }) {
  const { unit } = useStruktur()
  const [tambahBuka, setTambahBuka] = useState(false)
  const [rahasia, setRahasia] = useState<{ email: string; sandi: string } | null>(null)
  const daftar = useLoad(() => adminService.daftarKeanggotaan({ prodi_id: prodiId, ukuran: 200 }), [prodiId])
  const nama = useOrang((daftar.data?.data ?? []).map((item) => item.orang_id))
  const { isSuper } = useStruktur()
  const rows = daftar.data?.data ?? []

  return <Kartu judul="Mahasiswa program studi" aksi={isSuper ? <Button type="primary" onClick={() => setTambahBuka(true)}>+ Tambah mahasiswa</Button> : undefined}>
    <p className="adm-muted">Daftar mahasiswa yang terdaftar di program studi ini. Pembuatan akun bersifat opsional dan dapat dilakukan dari menu Orang & akun.</p>
    {daftar.error && <Notice tone="error">{daftar.error}</Notice>}
    <Table<Keanggotaan> rowKey="id" loading={daftar.loading} dataSource={rows} pagination={{ pageSize: 10, showSizeChanger: false, showTotal: (total) => `${total} mahasiswa` }} scroll={{ x: 680 }} locale={{ emptyText: 'Belum ada mahasiswa terdaftar.' }} columns={[
      { title: 'Nama mahasiswa', key: 'nama', render: (_, row) => nama(row.orang_id) },
      { title: 'Angkatan', dataIndex: 'angkatan', render: (value: number | null) => value ?? '—' },
      { title: 'Status', dataIndex: 'status', render: (value: string, row) => <Tag color={row.selesai ? 'default' : value === 'aktif' ? 'success' : 'warning'}>{row.selesai ? 'Selesai' : value}</Tag> },
      { title: 'Mulai', dataIndex: 'mulai', render: (value: string) => tanggal(value) },
      { title: 'Selesai', dataIndex: 'selesai', render: (value: string | null) => tanggal(value) },
    ]} />
    <Modal open={tambahBuka} title="Tambah mahasiswa ke program studi" footer={null} onCancel={() => setTambahBuka(false)}>
      <FormMahasiswa prodiId={prodiId} onSelesai={(secret) => { setTambahBuka(false); if (secret) setRahasia(secret); void daftar.reload() }} />
    </Modal>
    {rahasia && <Modal open title="Sandi sementara mahasiswa" footer={null} closable={false} maskClosable={false} keyboard={false}><SandiSementara {...rahasia} onClose={() => setRahasia(null)} /></Modal>}
  </Kartu>
}
