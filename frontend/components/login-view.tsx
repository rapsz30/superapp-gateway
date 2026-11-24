'use client'

import { useEffect, useState, type FormEvent } from 'react'
import { useRouter } from 'next/navigation'
import { Eye, EyeOff } from 'lucide-react'
import { errorMessage, tokenStore } from '@/src/lib/api'
import { authService } from '@/src/services/auth-service'

const loginArtwork = '/images/student-gateway-login-asset.svg'
const facultyOptions = ['Fakultas Teknik', 'Teknologi Industri']
const studyProgramOptions = ['Informatika']

export function LoginView() {
  const router = useRouter()
  const [register, setRegister] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [showRecoveryHelp, setShowRecoveryHelp] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [formNotice, setFormNotice] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  useEffect(() => {
    // Sudah punya sesi: langsung ke beranda (sesi yang kedaluwarsa akan dibersihkan oleh apiFetch).
    if (tokenStore.get()) router.replace('/beranda')
  }, [router])

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (submitting) return
    const formData = new FormData(event.currentTarget)
    const normalizedEmail = email.trim().toLowerCase()

    if (register && password !== confirmPassword) {
      setFormNotice({ type: 'error', message: 'Konfirmasi kata sandi tidak cocok.' })
      return
    }

    setSubmitting(true)
    try {
      if (register) {
        await authService.register({
          email: normalizedEmail,
          password,
          full_name: String(formData.get('fullName') ?? '').trim(),
          nim: String(formData.get('nim') ?? '').trim(),
          faculty: String(formData.get('faculty') ?? ''),
          study_program: String(formData.get('studyProgram') ?? ''),
        })
        setPassword('')
        setConfirmPassword('')
        setFormNotice({ type: 'success', message: 'Akun berhasil dibuat. Silakan masuk dengan email dan kata sandi Anda.' })
        setRegister(false)
        setShowRecoveryHelp(false)
        return
      }

      await authService.login(normalizedEmail, password)
      setFormNotice(null)
      router.push('/beranda')
    } catch (error) {
      setFormNotice({ type: 'error', message: errorMessage(error, 'Tidak dapat memproses permintaan. Coba lagi.') })
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
      <section className="login-panel" aria-labelledby="login-title">
        <form
          className={register ? 'login-form login-form-register' : 'login-form'}
          onSubmit={handleSubmit}
        >
          <h2 id="login-title">{register ? 'Buat akun baru' : 'Masuk ke Student Gateway'}</h2>
          {formNotice && <p className={`login-notice login-notice-${formNotice.type}`} role={formNotice.type === 'error' ? 'alert' : 'status'}>{formNotice.message}</p>}
          {register && (
            <label className="field">
              <span>Nama lengkap</span>
              <input name="fullName" autoComplete="name" placeholder="Nama sesuai data kampus" required />
            </label>
          )}
          <label className="field">
            <span>Email</span>
            <input name="email" type="email" autoComplete="email" value={email} onChange={(event) => { setEmail(event.target.value); setFormNotice(null) }} placeholder="Masukkan email" required />
          </label>
          {register && (
            <>
              <label className="field">
                <span>NIM</span>
                <input name="nim" inputMode="numeric" pattern="[0-9]{6,15}" title="NIM terdiri dari 6 sampai 15 digit angka" autoComplete="off" placeholder="Masukkan NIM" required />
              </label>
              <label className="field">
                <span>Fakultas</span>
                <select name="faculty" defaultValue="" required>
                  <option value="" disabled>Pilih fakultas</option>
                  {facultyOptions.map((faculty) => <option key={faculty} value={faculty}>{faculty}</option>)}
                </select>
              </label>
              <label className="field">
                <span>Program studi</span>
                <select name="studyProgram" defaultValue="" required>
                  <option value="" disabled>Pilih program studi</option>
                  {studyProgramOptions.map((program) => <option key={program} value={program}>{program}</option>)}
                </select>
              </label>
            </>
          )}
          <label className="field">
            <span>{register ? 'Kata sandi' : 'Password'}</span>
            <span className="password-field-wrap">
              <input name="password" type={showPassword ? 'text' : 'password'} value={password} onChange={(event) => { setPassword(event.target.value); setFormNotice(null) }} autoComplete={register ? 'new-password' : 'current-password'} minLength={register ? 8 : undefined} placeholder={register ? 'Masukkan kata sandi' : 'Masukkan password'} required />
              <button className="password-reveal" type="button" onClick={() => setShowPassword((visible) => !visible)} aria-label={showPassword ? 'Sembunyikan password' : 'Tampilkan password'} aria-pressed={showPassword}>
                {showPassword ? <EyeOff aria-hidden="true" /> : <Eye aria-hidden="true" />}
              </button>
            </span>
          </label>
          {register && (
            <label className="field">
              <span>Konfirmasi kata sandi</span>
              <input name="confirmPassword" type="password" value={confirmPassword} onChange={(event) => { setConfirmPassword(event.target.value); setFormNotice(null) }} autoComplete="new-password" placeholder="Masukkan ulang kata sandi" required />
            </label>
          )}
          {!register && <>
            <button className="login-forgot" type="button" onClick={() => setShowRecoveryHelp((visible) => !visible)}>Lupa password?</button>
            {showRecoveryHelp && <p className="login-recovery-help" role="status">Hubungi admin kampus untuk bantuan mengatur ulang password.</p>}
          </>}
          <button className="login-submit" type="submit" disabled={submitting}>{submitting ? 'Memproses...' : register ? 'Daftar' : 'Masuk'}</button>
          <p className="login-switch">{register ? 'Sudah punya akun?' : 'Belum punya akun?'}{' '}
            <button type="button" onClick={() => { setRegister((value) => !value); setShowRecoveryHelp(false); setFormNotice(null); setPassword(''); setConfirmPassword('') }}>{register ? 'Masuk' : 'Daftar'}</button>
          </p>
        </form>
      </section>
    </main>
  )
}
