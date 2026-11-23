'use client'

import { useState, type FormEvent } from 'react'
import { useRouter } from 'next/navigation'
import { Eye, EyeOff } from 'lucide-react'

const loginArtwork = '/images/student-gateway-login-asset.svg'
const facultyOptions = ['Fakultas Teknik', 'Teknologi Industri']
const studyProgramOptions = ['Informatika']

type FrontendAccount = {
  fullName: string
  email: string
  nim: string
  faculty: string
  studyProgram: string
  password: string
}

export function LoginView() {
  const router = useRouter()
  const [register, setRegister] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [showRecoveryHelp, setShowRecoveryHelp] = useState(false)
  const [createdAccount, setCreatedAccount] = useState<FrontendAccount | null>(null)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [formNotice, setFormNotice] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const formData = new FormData(event.currentTarget)

    if (register) {
      if (password !== confirmPassword) {
        setFormNotice({ type: 'error', message: 'Konfirmasi kata sandi tidak cocok.' })
        return
      }

      setCreatedAccount({
        fullName: String(formData.get('fullName') ?? '').trim(),
        email: email.trim().toLowerCase(),
        nim: String(formData.get('nim') ?? '').trim(),
        faculty: String(formData.get('faculty') ?? ''),
        studyProgram: String(formData.get('studyProgram') ?? ''),
        password,
      })
      setPassword('')
      setConfirmPassword('')
      setFormNotice({ type: 'success', message: 'Akun berhasil dibuat. Silakan masuk dengan email dan kata sandi Anda.' })
      setRegister(false)
      setShowRecoveryHelp(false)
      return
    }

    if (!createdAccount) {
      setFormNotice({ type: 'error', message: 'Buat akun terlebih dahulu sebelum masuk.' })
      return
    }

    if (email.trim().toLowerCase() !== createdAccount.email || password !== createdAccount.password) {
      setFormNotice({ type: 'error', message: 'Email atau kata sandi tidak sesuai dengan akun yang dibuat.' })
      return
    }

    setFormNotice(null)
    router.push('/beranda')
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
                <input name="nim" inputMode="numeric" autoComplete="off" placeholder="Masukkan NIM" required />
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
              <input name="password" type={showPassword ? 'text' : 'password'} value={password} onChange={(event) => { setPassword(event.target.value); setFormNotice(null) }} autoComplete={register ? 'new-password' : 'current-password'} placeholder={register ? 'Masukkan kata sandi' : 'Masukkan password'} required />
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
          <button className="login-submit" type="submit">{register ? 'Daftar' : 'Masuk'}</button>
          <p className="login-switch">{register ? 'Sudah punya akun?' : 'Belum punya akun?'}{' '}
            <button type="button" onClick={() => { setRegister((value) => !value); setShowRecoveryHelp(false); setFormNotice(null); setPassword(''); setConfirmPassword('') }}>{register ? 'Masuk' : 'Daftar'}</button>
          </p>
        </form>
      </section>
    </main>
  )
}
