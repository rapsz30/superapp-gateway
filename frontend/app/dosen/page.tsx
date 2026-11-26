'use client'
import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useDosen } from '@/components/dosen/dosen-shell'

export default function DosenPage() {
  const router = useRouter()
  const dosen = useDosen()
  useEffect(() => {
    router.replace(dosen.roles.includes('dosen_pa') || dosen.roles.includes('kaprodi') ? '/dosen/judul' : '/dosen/tema-judul')
  }, [router, dosen])
  return null
}
