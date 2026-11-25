'use client'

import { LockKeyhole, UserRound } from 'lucide-react'
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
}

export function ProfileView({ profile }: ProfileViewProps) {
  const { t } = useLanguage()

  return (
    <section className="profile-view" aria-labelledby="profile-title">
      <header className="profile-page-heading">
        <div className="profile-page-icon"><UserRound aria-hidden="true" /></div>
        <div>
          <p className="eyebrow">{t('Profil mahasiswa')}</p>
          <h1 id="profile-title">{t('Profil saya')}</h1>
          <p>{t('Data akademik Anda dikelola oleh admin kampus.')}</p>
        </div>
      </header>

      <form className="profile-card" onSubmit={(event) => event.preventDefault()}>
        <div className="profile-card-heading">
          <div>
            <h2>{t('Informasi pribadi')}</h2>
            <p>{t('Data ini tidak dapat diubah sendiri. Hubungi admin akademik bila ada yang keliru.')}</p>
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
            <input id="profile-name" value={profile.name} readOnly autoComplete="name" maxLength={100} />
          </label>
          <label className="profile-field" htmlFor="profile-nim">
            <span>{t('Nomor Induk Mahasiswa (NIM)')}</span>
            <input id="profile-nim" value={profile.nim} readOnly inputMode="numeric" maxLength={30} />
          </label>
          <label className="profile-field" htmlFor="profile-faculty">
            <span>{t('Fakultas')}</span>
            <input id="profile-faculty" value={profile.faculty} readOnly maxLength={100} />
          </label>
          <label className="profile-field" htmlFor="profile-major">
            <span>{t('Program studi')}</span>
            <input id="profile-major" value={profile.major} readOnly maxLength={100} />
          </label>
        </div>

      </form>
    </section>
  )
}
