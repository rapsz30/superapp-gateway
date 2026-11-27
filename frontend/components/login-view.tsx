'use client'

import { useEffect, useState, type FormEvent } from 'react'
import { useRouter } from 'next/navigation'
import { Eye, EyeOff } from 'lucide-react'
import { BrandLogo } from '@/components/brand'
import { errorMessage, tokenStore } from '@/src/lib/api'
import { authService } from '@/src/services/auth-service'

const loginArtwork = '/images/student-gateway-login-asset.svg'
// Harus sama dengan kebijakan layanan identity.
const MIN_PASSWORD_LENGTH = 10

/** Dosen dan kaprodi yang bukan mahasiswa langsung ke ruang dosen. */
function halamanAwal(roles: string[]): string {
  return !roles.includes('mahasiswa') && roles.some((r) => r === 'dosen_pa' || r === 'kaprodi') ? '/dosen' : '/beranda'
}

export function LoginView() {
  const router = useRouter()
  // 'ganti': akun baru dibuat admin dengan sandi sementara, wajib diganti sebelum memakai layanan.
  const [mode, setMode] = useState<'masuk' | 'ganti'>('masuk')
  const [showPassword, setShowPassword] = useState(false)
  const [showRecoveryHelp, setShowRecoveryHelp] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [formNotice, setFormNotice] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  useEffect(() => {
    // Sudah punya sesi: langsung ke beranda (sesi yang kedaluwarsa akan dibersihkan oleh apiFetch).
    if (tokenStore.get()) router.replace('/beranda')
  }, [router])

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (submitting) return

    if (mode === 'ganti') {
      if (newPassword.length < MIN_PASSWORD_LENGTH) {
        setFormNotice({ type: 'error', message: `Kata sandi baru minimal ${MIN_PASSWORD_LENGTH} karakter.` })
        return
      }
      if (newPassword !== confirmPassword) {
        setFormNotice({ type: 'error', message: 'Konfirmasi kata sandi tidak cocok.' })
        return
      }
    }

    setSubmitting(true)
    try {
      if (mode === 'ganti') {
        await authService.changePassword(password, newPassword)
        setFormNotice(null)
        router.push(halamanAwal((await authService.me()).roles))
        return
      }

      const user = await authService.login(email.trim().toLowerCase(), password)
      if (user.mustChangePassword) {
        setMode('ganti')
        setFormNotice({ type: 'success', message: 'Kata sandi Anda masih sementara. Buat kata sandi baru untuk melanjutkan.' })
        return
      }
      setFormNotice(null)
      router.push(halamanAwal(user.roles))
    } catch (error) {
      setFormNotice({ type: 'error', message: errorMessage(error, 'Tidak dapat memproses permintaan. Coba lagi.') })
    } finally {
      setSubmitting(false)
    }
  }

  const changing = mode === 'ganti'

  return (
    <main className="login-page">
      <section className="login-art" aria-label="Tentang Student Gateway">
        <div className="login-art-stage">
          <img src={loginArtwork} alt="" />
          <h1 className="login-art-caption">Satu akun untuk semua<br />layanan akademik Anda</h1>
        </div>
      </section>
      <section className="login-panel" aria-labelledby="login-title">
        <form className={changing ? 'login-form login-form-register' : 'login-form'} onSubmit={handleSubmit}>
          <BrandLogo variant="horizontal" className="login-brand-logo" />
          <h2 id="login-title">{changing ? 'Buat kata sandi baru' : 'Masuk'}</h2>
          {formNotice && <p className={`login-notice login-notice-${formNotice.type}`} role={formNotice.type === 'error' ? 'alert' : 'status'}>{formNotice.message}</p>}
          {!changing && (
            <>
              <label className="field">
                <span>Email</span>
                <input name="email" type="email" autoComplete="email" value={email} onChange={(event) => { setEmail(event.target.value); setFormNotice(null) }} placeholder="Masukkan email" required />
              </label>
              <label className="field">
                <span>Password</span>
                <span className="password-field-wrap">
                  <input name="password" type={showPassword ? 'text' : 'password'} value={password} onChange={(event) => { setPassword(event.target.value); setFormNotice(null) }} autoComplete="current-password" placeholder="Masukkan password" required />
                  <button className="password-reveal" type="button" onClick={() => setShowPassword((visible) => !visible)} aria-label={showPassword ? 'Sembunyikan password' : 'Tampilkan password'} aria-pressed={showPassword}>
                    {showPassword ? <EyeOff aria-hidden="true" /> : <Eye aria-hidden="true" />}
                  </button>
                </span>
              </label>
              <button className="login-forgot" type="button" onClick={() => setShowRecoveryHelp((visible) => !visible)}>Lupa password?</button>
              {showRecoveryHelp && <p className="login-recovery-help" role="status">Hubungi admin kampus untuk bantuan mengatur ulang password.</p>}
            </>
          )}
          {changing && (
            <>
              <label className="field">
                <span>Kata sandi baru</span>
                <span className="password-field-wrap">
                  <input name="newPassword" type={showPassword ? 'text' : 'password'} value={newPassword} onChange={(event) => { setNewPassword(event.target.value); setFormNotice(null) }} autoComplete="new-password" minLength={MIN_PASSWORD_LENGTH} placeholder={`Minimal ${MIN_PASSWORD_LENGTH} karakter`} required />
                  <button className="password-reveal" type="button" onClick={() => setShowPassword((visible) => !visible)} aria-label={showPassword ? 'Sembunyikan password' : 'Tampilkan password'} aria-pressed={showPassword}>
                    {showPassword ? <EyeOff aria-hidden="true" /> : <Eye aria-hidden="true" />}
                  </button>
                </span>
              </label>
              <label className="field">
                <span>Konfirmasi kata sandi baru</span>
                <input name="confirmPassword" type="password" value={confirmPassword} onChange={(event) => { setConfirmPassword(event.target.value); setFormNotice(null) }} autoComplete="new-password" placeholder="Masukkan ulang kata sandi baru" required />
              </label>
            </>
          )}
          <button className="login-submit" type="submit" disabled={submitting}>{submitting ? 'Memproses...' : changing ? 'Simpan dan lanjut' : 'Masuk'}</button>
          {!changing && <p className="login-switch">Akun dibuat oleh admin kampus. Belum punya akun? Hubungi admin akademik prodi Anda.</p>}
        </form>
      </section>
    </main>
  )
}
