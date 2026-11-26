'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Alert, App, Button, Card, Descriptions, Flex, Input, Spin, Table, Typography } from 'antd'
import { ArrowLeftOutlined, CheckOutlined, RollbackOutlined } from '@ant-design/icons'
import { errorMessage } from '@/src/lib/api'
import { dosenService } from '@/src/services/dosen-service'
import { TagKeadaan, useMuat, waktu } from './bersama'
import { useDosen } from './dosen-shell'

export function DetailPengajuan({ id }: { id: string }) {
  const dosen = useDosen()
  const router = useRouter()
  const { message, modal } = App.useApp()
  const { data: p, galat, memuat, muat } = useMuat(id, () => dosenService.ambil(id), 8_000)
  const [catatan, setCatatan] = useState('')
  const [wajibCatatan, setWajibCatatan] = useState(false)
  const [mengirim, setMengirim] = useState<'setuju' | 'revisi' | null>(null)

  if (!p) {
    return memuat ? <Spin size="large" /> : <Alert type="error" showIcon title={galat || 'Pengajuan tidak ditemukan.'} action={<Button onClick={() => router.back()}>Kembali</Button>} />
  }

  const sayaDpa = p.dpa?.id === dosen.id
  const menunggu = p.status === 'diajukan' && p.tahap === 'tinjau'
  const bacaan = p.hasil_bacaan ?? {}
  const rencana = p.rencana ?? null

  async function kirim(keputusan: 'setuju' | 'revisi') {
    setMengirim(keputusan)
    try {
      await dosenService.putuskan(id, keputusan, catatan)
      message.success(keputusan === 'setuju' ? 'Rencana studi disetujui.' : 'Permintaan revisi dikirim.')
      setCatatan('')
    } catch (error) {
      message.error(errorMessage(error))
    } finally {
      await muat()
      setMengirim(null)
    }
  }

  function setujui() {
    modal.confirm({
      title: 'Setujui rencana studi ini?',
      content: `${p?.mahasiswa?.nama_lengkap ?? 'Mahasiswa'}, semester ${p?.semester_target}, ${rencana?.total_sks ?? 0} SKS. Keputusan tidak dapat diubah.`,
      okText: 'Setujui',
      cancelText: 'Batal',
      onOk: () => kirim('setuju'),
    })
  }

  function mintaRevisi() {
    if (!catatan.trim()) {
      setWajibCatatan(true)
      return
    }
    void kirim('revisi')
  }

  return (
    <Flex vertical gap={16}>
      <div><Button icon={<ArrowLeftOutlined />} onClick={() => router.back()}>Kembali</Button></div>
      {galat && <Alert type="error" showIcon title={galat} />}
      {p.pesan_galat && <Alert type="error" showIcon title="Proses bermasalah" description={p.pesan_galat} />}

      <Card title={p.mahasiswa?.nama_lengkap ?? 'Mahasiswa'} extra={<TagKeadaan p={p} />}>
        <Descriptions column={{ xs: 1, md: 2 }} items={[
          { key: 'nim', label: 'NIM', children: p.mahasiswa?.nim ?? '—' },
          { key: 'prodi', label: 'Program studi', children: p.prodi?.nama ?? '—' },
          { key: 'semester', label: 'Semester tujuan', children: p.semester_target },
          { key: 'dpa', label: 'Pembimbing akademik', children: p.dpa?.nama_lengkap ?? '—' },
          { key: 'panduan', label: 'Panduan dipakai', children: `Versi ${p.panduan.versi}${p.panduan.versi_aktif_sekarang && p.panduan.versi_aktif_sekarang !== p.panduan.versi ? ` (yang aktif sekarang versi ${p.panduan.versi_aktif_sekarang})` : ''}` },
          { key: 'diajukan', label: 'Diajukan', children: waktu(p.diajukan_pada) },
          { key: 'revisi', label: 'Jumlah revisi', children: p.jumlah_revisi },
          { key: 'putus', label: 'Diputuskan', children: waktu(p.diputuskan_pada) },
        ]} />
        {p.catatan_dpa && <Alert type="info" showIcon title="Catatan pembimbing akademik" description={p.catatan_dpa} />}
      </Card>

      <Card title="Hasil bacaan KHS">
        {bacaan.nim_cocok === false && <Alert type="error" showIcon title="NIM pada KHS berbeda dengan NIM akun mahasiswa." style={{ marginBottom: 12 }} />}
        <Descriptions column={{ xs: 1, md: 3 }} items={[
          { key: 'ipk', label: 'IPK', children: bacaan.ipk ?? '—' },
          { key: 'sks', label: 'SKS lulus', children: bacaan.sks_lulus ?? '—' },
          { key: 'yakin', label: 'Keyakinan bacaan', children: typeof bacaan.keyakinan === 'number' ? `${Math.round(bacaan.keyakinan * 100)}%` : '—' },
          { key: 'ulang', label: 'Mata kuliah wajib diulang', children: bacaan.mk_ulang?.length ? bacaan.mk_ulang.join(', ') : 'Tidak ada' },
        ]} />
      </Card>

      <Card title="Rencana studi yang direkomendasikan">
        {!rencana?.rencana_mk?.length ? <Typography.Text type="secondary">Rencana belum tersedia.</Typography.Text> : (
          <Flex vertical gap={12}>
            {rencana.peringatan?.map((teks) => <Alert key={teks} type="warning" showIcon title={teks} />)}
            <Table
              rowKey="kode"
              dataSource={rencana.rencana_mk}
              pagination={false}
              scroll={{ x: 'max-content' }}
              columns={[
                { title: 'Kode', dataIndex: 'kode' },
                { title: 'Mata kuliah', dataIndex: 'nama' },
                { title: 'SKS', dataIndex: 'sks', render: (v: number | null) => v ?? '—' },
                { title: 'Alasan', dataIndex: 'alasan', width: 360 },
              ]}
            />
            <Typography.Text strong>Total: {rencana.total_sks ?? '—'} SKS</Typography.Text>
            {rencana.alasan && <Typography.Paragraph>{rencana.alasan}</Typography.Paragraph>}
          </Flex>
        )}
      </Card>

      {sayaDpa && menunggu && (
        <Card title="Keputusan Anda">
          <Flex vertical gap={12}>
            <div>
              <Input.TextArea aria-label="Catatan untuk mahasiswa" rows={3} maxLength={2000} showCount value={catatan} status={wajibCatatan ? 'error' : undefined}
                onChange={(e) => { setCatatan(e.target.value); setWajibCatatan(false) }}
                placeholder="Catatan (wajib bila meminta revisi), misalnya: maksimal 18 SKS, dahulukan mata kuliah yang diulang." />
              {wajibCatatan && <Typography.Text type="danger">Isi catatan supaya rencana dapat direvisi.</Typography.Text>}
            </div>
            <Flex gap={8} wrap style={{ marginTop: 8 }}>
              <Button type="primary" icon={<CheckOutlined />} loading={mengirim === 'setuju'} disabled={mengirim !== null} onClick={setujui}>Setujui</Button>
              <Button icon={<RollbackOutlined />} loading={mengirim === 'revisi'} disabled={mengirim !== null} onClick={mintaRevisi}>Minta revisi</Button>
            </Flex>
          </Flex>
        </Card>
      )}
    </Flex>
  )
}
