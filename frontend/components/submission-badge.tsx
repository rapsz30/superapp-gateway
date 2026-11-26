import { AlertTriangle, Ban, CheckCircle2, Hourglass, Loader2, RefreshCw, ScanSearch, type LucideIcon } from 'lucide-react'
import type { Submission } from '@/src/services/pengajuan-service'

type Tone = 'info' | 'warning' | 'success' | 'danger' | 'neutral'

/** Label status dari keadaan proses yang sebenarnya (status akhir, atau tahap selama masih berjalan). */
function describe({ status, tahap, pesan_galat }: Submission): { label: string; tone: Tone; Icon: LucideIcon; spin?: boolean } {
  if (status === 'disetujui') return { label: 'Disetujui', tone: 'success', Icon: CheckCircle2 }
  if (status === 'ditolak') return { label: 'Ditolak', tone: 'danger', Icon: Ban }
  if (status === 'dibatalkan') return { label: 'Dibatalkan', tone: 'neutral', Icon: Ban }
  if (pesan_galat) return { label: 'Proses bermasalah', tone: 'danger', Icon: AlertTriangle }
  if (tahap === 'periksa') return { label: 'Perlu Anda periksa', tone: 'warning', Icon: ScanSearch }
  if (tahap === 'tinjau') return { label: 'Menunggu pembimbing akademik', tone: 'info', Icon: Hourglass }
  if (tahap === 'revisi' || status === 'revisi') return { label: 'Sedang direvisi', tone: 'warning', Icon: RefreshCw }
  return { label: 'Sedang diproses', tone: 'info', Icon: Loader2, spin: true }
}

export function SubmissionBadge({ submission }: { submission: Submission }) {
  const { label, tone, Icon, spin } = describe(submission)
  return <span className="status-badge" data-tone={tone} role="status"><Icon className={spin ? 'spin' : undefined} aria-hidden="true" />{label}</span>
}
