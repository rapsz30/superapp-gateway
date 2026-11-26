'use client'

import { useRouter } from 'next/navigation'
import { CourseRecommendation } from '@/components/course-recommendation'
import { useCurrentUser } from '@/src/hooks/use-current-user'

export function MatkulPage({ mode }: { mode: 'dashboard' | 'pengajuan' }) {
  const router = useRouter()
  const { user } = useCurrentUser()
  const profile = {
    name: user?.full_name || user?.email || 'Mahasiswa',
    nim: user?.nim || '-',
    faculty: user?.faculty || '-',
    program: user?.study_program || '-',
  }

  return <CourseRecommendation
    studentId={user?.roles.includes('mahasiswa') ? user.id : undefined}
    studentFallback={profile}
    startInWorkflow={mode === 'pengajuan'}
    onStart={() => router.push('/matkul/pengajuan')}
    onBackToDashboard={() => router.push('/matkul/beranda')}
  />
}
