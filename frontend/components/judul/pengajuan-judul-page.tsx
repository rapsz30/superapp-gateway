'use client'

import { useEffect, useState } from 'react'
import { Loader2 } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { JudulForm } from '@/components/judul/judul-form'
import { errorMessage } from '@/src/lib/api'
import { judulService, type ThesisAdvisorOption, type ThesisMine, type ThesisSubmissionInput } from '@/src/services/judul-service'

const DRAFT_KEY = 'judul-form-pengajuan'
const EMPTY_FORM: ThesisSubmissionInput = { topik: '', judul: '', tema: '', deskripsi: '', metodologi: '', keywords: [], referensi: [] }

interface FormDraft {
  form?: ThesisSubmissionInput
  isRevision?: boolean
  pengajuanId?: string | null
  pembimbingId?: string | null
}

export function PengajuanJudulPage() {
  const router = useRouter()
  const [form, setForm] = useState<ThesisSubmissionInput>(EMPTY_FORM)
  const [themes, setThemes] = useState<string[]>([])
  const [advisors, setAdvisors] = useState<ThesisAdvisorOption[]>([])
  const [mine, setMine] = useState<ThesisMine | null>(null)
  const [selectedAdvisorId, setSelectedAdvisorId] = useState('')
  const [isRevision, setIsRevision] = useState(false)
  const [pengajuanId, setPengajuanId] = useState<string | null>(null)
  const [draftReady, setDraftReady] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let draft: FormDraft = {}
    try {
      const raw = sessionStorage.getItem(DRAFT_KEY)
      if (raw) draft = JSON.parse(raw) as FormDraft
    } catch {
      sessionStorage.removeItem(DRAFT_KEY)
    }

    setForm(draft.form ?? EMPTY_FORM)
    setIsRevision(!!draft.isRevision)
    setPengajuanId(draft.pengajuanId ?? null)
    setSelectedAdvisorId(draft.pembimbingId ?? '')
    setDraftReady(true)

    async function load() {
      try {
        const [tema, saya] = await Promise.all([judulService.tema(), judulService.saya()])
        setThemes(tema)
        setMine(saya)
        if (!draft.isRevision) {
          const daftar = await judulService.daftarPembimbing()
          setAdvisors(daftar)
          const pilihan = draft.pembimbingId && daftar.some((item) => item.id === draft.pembimbingId)
            ? draft.pembimbingId
            : saya.pembimbing?.id && daftar.some((item) => item.id === saya.pembimbing?.id)
              ? saya.pembimbing.id
              : daftar[0]?.id ?? ''
          setSelectedAdvisorId(pilihan)
        }
      } catch (caught) {
        setError(errorMessage(caught, 'Data pengajuan belum dapat dimuat.'))
      } finally {
        setLoading(false)
      }
    }
    void load()
  }, [])

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    if (!isRevision && !selectedAdvisorId) {
      setError('Pilih dosen pembimbing sebelum mengirim pengajuan.')
      return
    }
    if (isRevision && !pengajuanId) {
      setError('Data pengajuan yang akan direvisi tidak ditemukan. Buka ulang dari halaman obrolan.')
      return
    }
    const advisor = advisors.find((item) => item.id === selectedAdvisorId)
    const namaPembimbing = isRevision ? mine?.pengajuan?.pembimbing?.nama_lengkap : advisor?.nama_lengkap
    if (!window.confirm(`Kirim judul ini${namaPembimbing ? ` kepada ${namaPembimbing}` : ''}?`)) return

    setSaving(true)
    setError('')
    try {
      if (isRevision && pengajuanId) await judulService.ubah(pengajuanId, form)
      else await judulService.ajukan({ ...form, pembimbing_id: selectedAdvisorId })
      sessionStorage.removeItem(DRAFT_KEY)
      router.push('/judul/beranda')
    } catch (caught) {
      setError(errorMessage(caught, 'Pengajuan judul tidak dapat dikirim.'))
    } finally {
      setSaving(false)
    }
  }

  function back() {
    sessionStorage.removeItem(DRAFT_KEY)
    router.push('/judul/rekomendasi')
  }

  if (!draftReady) return <div className="page-content judul-application-page"><div className="judul-advisor-loading"><Loader2 className="spin" /> Menyiapkan formulir...</div></div>

  return <JudulForm
    form={form}
    themes={themes}
    advisors={advisors}
    selectedAdvisorId={selectedAdvisorId}
    currentAdvisor={mine?.pengajuan?.pembimbing ?? mine?.pembimbing ?? null}
    loading={loading}
    saving={saving}
    error={error}
    isRevision={isRevision}
    onChange={(key, value) => { setForm((current) => ({ ...current, [key]: value })); setError('') }}
    onAdvisorChange={(id) => { setSelectedAdvisorId(id); setError('') }}
    onSubmit={(event) => void submit(event)}
    onBack={back}
  />
}
