'use client'

import { useState, type FormEvent } from 'react'
import { ArrowLeft, CheckCircle2, Eye, EyeOff, KeyRound, MailCheck, ShieldCheck } from 'lucide-react'
import { useLanguage } from '@/components/language-provider'

type AccountSettingsViewProps = {
  email: string
}

type ResetStep = 'settings' | 'email' | 'email-sent' | 'reset' | 'done'

export function AccountSettingsView({ email: initialEmail }: AccountSettingsViewProps) {
  const { t } = useLanguage()
  const [step, setStep] = useState<ResetStep>('settings')
  const [email, setEmail] = useState(initialEmail)
  const [feedback, setFeedback] = useState('')
  const [passwordMismatch, setPasswordMismatch] = useState(false)

  function handlePasswordChange(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const values = new FormData(form)
    const newPassword = String(values.get('newPassword') ?? '')
    const confirmation = String(values.get('confirmPassword') ?? '')

    if (newPassword !== confirmation) {
      setPasswordMismatch(true)
      setFeedback(t('Konfirmasi kata sandi baru tidak cocok.'))
      return
    }

    setPasswordMismatch(false)
    form.reset()
    setFeedback(t('Kata sandi berhasil diubah.'))
  }

  function handleEmailSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setStep('email-sent')
  }

  function handleResetSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const values = new FormData(form)

    if (values.get('newPassword') !== values.get('confirmPassword')) {
      setPasswordMismatch(true)
      setFeedback(t('Konfirmasi kata sandi baru tidak cocok.'))
      return
    }

    setPasswordMismatch(false)
    form.reset()
    setStep('done')
  }

  function handlePasswordEdit(form: HTMLFormElement) {
    if (!passwordMismatch) return

    const values = new FormData(form)
    const mismatch = values.get('newPassword') !== values.get('confirmPassword')
    setPasswordMismatch(mismatch)

    if (!mismatch) setFeedback('')
  }

  function returnToSettings() {
    setStep('settings')
    setFeedback('')
    setPasswordMismatch(false)
  }

  return (
    <section className="account-settings" aria-labelledby="account-settings-title">
      <header className="account-settings-heading">
        <div className="profile-page-icon"><ShieldCheck aria-hidden="true" /></div>
        <div>
          <p className="eyebrow">{t('Keamanan akun')}</p>
          <h1 id="account-settings-title">{t('Pengaturan akun')}</h1>
          <p>{t('Kelola kata sandi dan keamanan akun Anda.')}</p>
        </div>
      </header>

      <div className="account-settings-card">
        {step === 'settings' && (
          <>
            <div className="account-settings-card-heading">
              <div className="account-settings-card-icon"><KeyRound aria-hidden="true" /></div>
              <div>
                <h2>{t('Ubah kata sandi')}</h2>
                <p>{t('Masukkan kata sandi saat ini dan buat kata sandi baru.')}</p>
              </div>
            </div>
            <form className="account-settings-form" onSubmit={handlePasswordChange}>
              <PasswordField id="current-password" name="currentPassword" label={t('Kata sandi saat ini')} autoComplete="current-password" />
              <PasswordField id="new-password" name="newPassword" label={t('Kata sandi baru')} autoComplete="new-password" minLength={8} hint={t('Gunakan minimal 8 karakter.')} onValueChange={handlePasswordEdit} />
              <PasswordField id="confirm-password" name="confirmPassword" label={t('Ulangi kata sandi baru')} autoComplete="new-password" minLength={8} invalid={passwordMismatch} error={passwordMismatch ? feedback : undefined} onValueChange={handlePasswordEdit} />
              <button className="primary account-settings-submit" type="submit">{t('Simpan kata sandi')}</button>
              {feedback && !passwordMismatch && <p className="account-settings-feedback" role="status" aria-live="polite">{feedback}</p>}
            </form>
            <div className="account-reset-row">
              <button className="account-settings-link" type="button" onClick={() => { setFeedback(''); setPasswordMismatch(false); setStep('email') }}>{t('Lupa kata sandi?')}</button>
            </div>
          </>
        )}

        {step === 'email' && (
          <>
            <button className="account-settings-back" type="button" onClick={returnToSettings}><ArrowLeft aria-hidden="true" />{t('Kembali ke pengaturan akun')}</button>
            <div className="account-settings-card-heading">
              <div className="account-settings-card-icon"><MailCheck aria-hidden="true" /></div>
              <div>
                <h2>{t('Verifikasi alamat email')}</h2>
                <p>{t('Masukkan email akun untuk memulai simulasi reset kata sandi.')}</p>
              </div>
            </div>
            <form className="account-settings-form" onSubmit={handleEmailSubmit}>
              <div className="account-settings-field">
                <label htmlFor="reset-email">{t('Alamat email')}</label>
                <input id="reset-email" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
              </div>
              <button className="primary account-settings-submit" type="submit">{t('Lanjutkan verifikasi')}</button>
            </form>
          </>
        )}

        {step === 'email-sent' && (
          <div className="account-settings-result">
            <div className="account-settings-result-icon"><MailCheck aria-hidden="true" /></div>
            <h2>{t('Verifikasi email')}</h2>
            <p>{t('Dalam layanan nyata, tautan verifikasi akan dikirim ke')} <strong>{email}</strong>.</p>
            <p className="account-settings-result-note">{t('Tidak ada email yang benar-benar dikirim. Lanjutkan untuk melihat langkah reset.')}</p>
            <button className="primary account-settings-submit" type="button" onClick={() => { setFeedback(''); setPasswordMismatch(false); setStep('reset') }}>{t('Lanjutkan simulasi')}</button>
            <button className="account-settings-text-button" type="button" onClick={() => setStep('email')}>{t('Gunakan email lain')}</button>
          </div>
        )}

        {step === 'reset' && (
          <>
            <button className="account-settings-back" type="button" onClick={() => { setFeedback(''); setPasswordMismatch(false); setStep('email-sent') }}><ArrowLeft aria-hidden="true" />{t('Kembali')}</button>
            <div className="account-settings-card-heading">
              <div className="account-settings-card-icon"><KeyRound aria-hidden="true" /></div>
              <div>
                <h2>{t('Buat kata sandi baru')}</h2>
                <p>{t('Langkah verifikasi email simulasi selesai untuk')} {email}.</p>
              </div>
            </div>
            <form className="account-settings-form" onSubmit={handleResetSubmit}>
              <PasswordField id="reset-new-password" name="newPassword" label={t('Kata sandi baru')} autoComplete="new-password" minLength={8} hint={t('Gunakan minimal 8 karakter.')} onValueChange={handlePasswordEdit} />
              <PasswordField id="reset-confirm-password" name="confirmPassword" label={t('Ulangi kata sandi baru')} autoComplete="new-password" minLength={8} invalid={passwordMismatch} error={passwordMismatch ? feedback : undefined} onValueChange={handlePasswordEdit} />
              <button className="primary account-settings-submit" type="submit">{t('Simpan kata sandi baru')}</button>
            </form>
          </>
        )}

        {step === 'done' && (
          <div className="account-settings-result">
            <div className="account-settings-result-icon"><CheckCircle2 aria-hidden="true" /></div>
            <h2>{t('Simulasi reset selesai')}</h2>
            <p>{t('Kata sandi akun tidak diubah dan tidak ada email yang dikirim.')}</p>
            <button className="primary account-settings-submit" type="button" onClick={returnToSettings}>{t('Kembali ke pengaturan akun')}</button>
          </div>
        )}
      </div>
    </section>
  )
}

type PasswordFieldProps = {
  id: string
  name: string
  label: string
  autoComplete: string
  minLength?: number
  hint?: string
  invalid?: boolean
  error?: string
  onValueChange?: (form: HTMLFormElement) => void
}

function PasswordField({ id, name, label, autoComplete, minLength, hint, invalid, error, onValueChange }: PasswordFieldProps) {
  const { t } = useLanguage()
  const [isVisible, setIsVisible] = useState(false)

  return (
    <div className="account-settings-field">
      <label htmlFor={id}>{label}</label>
      <div className="account-password-input-wrap">
        <input id={id} name={name} type={isVisible ? 'text' : 'password'} autoComplete={autoComplete} minLength={minLength} aria-invalid={invalid || undefined} aria-describedby={error ? `${id}-error` : undefined} onChange={(event) => { if (event.currentTarget.form) onValueChange?.(event.currentTarget.form) }} required />
        <button className="account-password-toggle" type="button" aria-label={t(isVisible ? 'Sembunyikan kata sandi' : 'Tampilkan kata sandi')} aria-pressed={isVisible} onClick={() => setIsVisible((visible) => !visible)}>
          {isVisible ? <EyeOff aria-hidden="true" /> : <Eye aria-hidden="true" />}
        </button>
      </div>
      {error && <small id={`${id}-error`} className="account-settings-field-error" role="alert">{error}</small>}
      {hint && <small>{hint}</small>}
    </div>
  )
}
