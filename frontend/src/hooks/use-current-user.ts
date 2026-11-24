'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { tokenStore } from '@/src/lib/api'
import { authService, type AuthUser } from '@/src/services/auth-service'

/** Memuat profil pengguna dari backend. Tanpa token, pengguna dialihkan ke /login. */
export function useCurrentUser() {
  const router = useRouter()
  const [user, setUser] = useState<AuthUser | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!tokenStore.get()) {
      router.replace('/login')
      return
    }
    let active = true
    authService
      .me()
      .then((value) => {
        if (active) setUser(value)
      })
      .catch(() => {
        // 401 sudah dialihkan oleh apiFetch; error lain (layanan mati) dibiarkan tanpa profil.
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [router])

  return { user, setUser, loading }
}
