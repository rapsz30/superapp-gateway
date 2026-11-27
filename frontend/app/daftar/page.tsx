'use client'

import { useEffect, useState, type FormEvent } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Eye, EyeOff } from 'lucide-react'
import { BrandLogo } from '@/components/brand'
import { errorMessage, tokenStore } from '@/src/lib/api'
import { authService } from '@/src/services/auth-service'

const loginArtwork = '/images/student-gateway-login-asset.svg'
const MIN_PASSWORD_LENGTH = 10

export default function DaftarPage() {
  const router = useRouter()
  const [aktif, setAktif] = useState<boolean | null>(null)
  const [showPassword, setShowPassword] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [nama, setNama] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [prodi, setProdi] = useState('')
  const [pt, setPt] = useState('')
  const [formNotice, setFormNotice] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  useEffect(() => {
    if (tokenStore.get()) {
      router.replace('/beranda')
      return
    }
    void authService
      .statusRegistrasi()
      .then((a) => {
        setAktif(a)
        if (!a) setFormNotice({ type: 'error', message: 'Pendaftaran sedang ditutup.' })
      })
      .catch(() => {
        setAktif(false)
        setFormNotice({ type: 'error', message: 'Tidak dapat memeriksa status pendaftaran.' })
      })
  }, [router])

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (submitting || !aktif) return
    if (password.length < MIN_PASSWORD_LENGTH) {
      setFormNotice({ type: 'error', message: `Kata sandi minimal ${MIN_PASSWORD_LENGTH} karakter.` })
      return
    }
    if (password !== confirm) {
      setFormNotice({ type: 'error', message: 'Konfirmasi kata sandi tidak cocok.' })
      return
    }
    setSubmitting(true)
    try {
      await authService.register({
        nama_lengkap: nama.trim(),
        email: email.trim().toLowerCase(),
        sandi: password,
        program_studi: prodi.trim(),
        perguruan_tinggi: pt.trim(),
      })
      router.push('/beranda')
    } catch (error) {
      setFormNotice({ type: 'error', message: errorMessage(error, 'Pendaftaran gagal. Coba lagi.') })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="login-page">
      <section className="login-art" aria-label="Tentang Student Gateway">
        <div className="login-art-stage">
          <img src={loginArtwork} alt="" />
          <h1 className="login-art-caption">Satu akun untuk semua<br />layanan akademik Anda</h1>
        </div>
      </section>
      <section className="login-panel" aria-labelledby="daftar-title">
        <form className="login-form login-form-register" onSubmit={handleSubmit}>
          <BrandLogo variant="horizontal" className="login-brand-logo" />
          <h2 id="daftar-title">Daftar</h2>
          {formNotice && (
            <p className={`login-notice login-notice-${formNotice.type}`} role={formNotice.type === 'error' ? 'alert' : 'status'}>
              {formNotice.message}
            </p>
          )}
          <label className="field">
            <span>Nama lengkap</span>
            <input name="nama" type="text" autoComplete="name" value={nama} onChange={(e) => { setNama(e.target.value); setFormNotice(null) }} placeholder="Nama lengkap" required maxLength={200} disabled={!aktif} />
          </label>
          <label className="field">
            <span>Email</span>
            <input name="email" type="email" autoComplete="email" value={email} onChange={(e) => { setEmail(e.target.value); setFormNotice(null) }} placeholder="email@contoh.ac.id" required disabled={!aktif} />
          </label>
          <label className="field">
            <span>Program studi</span>
            <input name="prodi" type="text" value={prodi} onChange={(e) => { setProdi(e.target.value); setFormNotice(null) }} placeholder="Program studi Anda" required maxLength={200} disabled={!aktif} />
          </label>
          <label className="field">
            <span>Perguruan tinggi</span>
            <input name="pt" type="text" value={pt} onChange={(e) => { setPt(e.target.value); setFormNotice(null) }} placeholder="Nama perguruan tinggi" required maxLength={200} disabled={!aktif} />
          </label>
          <label className="field">
            <span>Kata sandi</span>
            <span className="password-field-wrap">
              <input name="password" type={showPassword ? 'text' : 'password'} value={password} onChange={(e) => { setPassword(e.target.value); setFormNotice(null) }} autoComplete="new-password" minLength={MIN_PASSWORD_LENGTH} placeholder={`Minimal ${MIN_PASSWORD_LENGTH} karakter`} required disabled={!aktif} />
              <button className="password-reveal" type="button" onClick={() => setShowPassword((v) => !v)} aria-label={showPassword ? 'Sembunyikan password' : 'Tampilkan password'} aria-pressed={showPassword}>
                {showPassword ? <EyeOff aria-hidden="true" /> : <Eye aria-hidden="true" />}
              </button>
            </span>
          </label>
          <label className="field">
            <span>Konfirmasi kata sandi</span>
            <input name="confirm" type="password" value={confirm} onChange={(e) => { setConfirm(e.target.value); setFormNotice(null) }} autoComplete="new-password" placeholder="Masukkan ulang kata sandi" required disabled={!aktif} />
          </label>
          <button className="login-submit" type="submit" disabled={submitting || !aktif}>
            {submitting ? 'Mendaftar...' : 'Daftar'}
          </button>
          <p className="login-switch">
            Sudah punya akun? <Link href="/login">Masuk</Link>
          </p>
        </form>
      </section>
    </main>
  )
}
