'use client'

import { useState } from 'react'
import { CheckCircle2, LockKeyhole, UserRound } from 'lucide-react'
import { useLanguage } from '@/components/language-provider'

type ProfileDetails = {
  email: string
  name: string
  nim: string
  faculty: string
  major: string
}

type ProfileViewProps = {
  profile: ProfileDetails
  onChange: (profile: ProfileDetails) => void
}

export function ProfileView({ profile, onChange }: ProfileViewProps) {
  const { t } = useLanguage()
  const [isSaved, setIsSaved] = useState(false)

  function updateField(field: keyof Omit<ProfileDetails, 'email'>, value: string) {
    onChange({ ...profile, [field]: value })
    setIsSaved(false)
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setIsSaved(true)
  }

  return (
    <section className="profile-view" aria-labelledby="profile-title">
      <header className="profile-page-heading">
        <div className="profile-page-icon"><UserRound aria-hidden="true" /></div>
        <div>
          <p className="eyebrow">{t('Profil mahasiswa')}</p>
          <h1 id="profile-title">{t('Profil saya')}</h1>
          <p>{t('Kelola informasi akademik dan identitas Anda.')}</p>
        </div>
      </header>

      <form className="profile-card" onSubmit={handleSubmit}>
        <div className="profile-card-heading">
          <div>
            <h2>{t('Informasi pribadi')}</h2>
            <p>{t('Perbarui data profil akademik Anda.')}</p>
          </div>
        </div>

        <div className="profile-fields">
          <label className="profile-field profile-field-readonly" htmlFor="profile-email">
            <span>{t('Alamat email')}</span>
            <div className="profile-input-wrap">
              <input id="profile-email" type="email" value={profile.email} readOnly aria-describedby="profile-email-hint" />
              <LockKeyhole aria-hidden="true" />
            </div>
            <small id="profile-email-hint">{t('Email tidak dapat diubah')}</small>
          </label>
          <label className="profile-field" htmlFor="profile-name">
            <span>{t('Nama lengkap')}</span>
            <input id="profile-name" value={profile.name} onChange={(event) => updateField('name', event.target.value)} autoComplete="name" maxLength={100} required />
          </label>
          <label className="profile-field" htmlFor="profile-nim">
            <span>{t('Nomor Induk Mahasiswa (NIM)')}</span>
            <input id="profile-nim" value={profile.nim} onChange={(event) => updateField('nim', event.target.value)} inputMode="numeric" maxLength={30} required />
          </label>
          <label className="profile-field" htmlFor="profile-faculty">
            <span>{t('Fakultas')}</span>
            <input id="profile-faculty" value={profile.faculty} onChange={(event) => updateField('faculty', event.target.value)} maxLength={100} required />
          </label>
          <label className="profile-field" htmlFor="profile-major">
            <span>{t('Jurusan')}</span>
            <input id="profile-major" value={profile.major} onChange={(event) => updateField('major', event.target.value)} maxLength={100} required />
          </label>
        </div>

        <div className="profile-form-footer">
          <p className="profile-save-status" role={isSaved ? 'alert' : undefined} aria-live="assertive">{isSaved && <><CheckCircle2 aria-hidden="true" />{t('Perubahan profil berhasil disimpan.')}</>}</p>
          <button className="primary profile-save-button" type="submit">{t('Simpan perubahan')}</button>
        </div>
      </form>
    </section>
  )
}
