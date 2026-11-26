'use client'

import { useCallback, useEffect, useState } from 'react'
import { errorMessage } from '@/src/lib/api'
import { pengajuanService, type Submission } from '@/src/services/pengajuan-service'

/**
 * Pengajuan terakhir milik mahasiswa (bukan data contoh): dimuat saat halaman dibuka, lalu diperbarui
 * tiap 5 detik selama masih berjalan. `studentId` kosong (bukan mahasiswa) berarti tidak memuat apa pun.
 */
export function usePengajuanSaya(studentId?: string) {
  const [submission, setSubmission] = useState<Submission | null>(null)
  const [loading, setLoading] = useState(!!studentId)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    if (!studentId) return
    let active = true
    setLoading(true)
    setError('')
    pengajuanService
      .findLatest(studentId)
      // Jangan menimpa pengajuan yang baru dikirim saat pemuatan ini masih berjalan.
      .then((latest) => { if (active && latest) setSubmission((current) => current ?? latest) })
      .catch((caught) => { if (active) setError(errorMessage(caught, 'Status pengajuan tidak dapat dimuat.')) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [studentId, attempt])

  useEffect(() => {
    if (submission?.status !== 'diajukan') return
    let active = true
    const timer = window.setInterval(() => {
      pengajuanService.get(submission.id).then((value) => { if (active) setSubmission(value) }).catch(() => undefined)
    }, 5_000)
    return () => { active = false; window.clearInterval(timer) }
  }, [submission?.id, submission?.status])

  const reload = useCallback(() => setAttempt((value) => value + 1), [])
  return [submission, setSubmission, { loading, error, reload }] as const
}
