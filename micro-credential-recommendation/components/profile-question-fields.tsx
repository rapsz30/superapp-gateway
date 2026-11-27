'use client'

import type { ChangeEvent } from 'react'

export type ProfileQuestionAnswer = {
  projectCount: string
  projectContexts: string[]
  technologies: string[]
  otherTechnologies: string
  duration: string
  payment: string
}

export const emptyProfileQuestionAnswer: ProfileQuestionAnswer = {
  projectCount: '',
  projectContexts: [],
  technologies: [],
  otherTechnologies: '',
  duration: '',
  payment: '',
}

const quickTechnologies = [
  'Docker', 'Kubernetes', 'AWS', 'GCP', 'Azure', 'GraphQL', 'Redis', 'Kafka',
  'Microservices', 'CI/CD', 'Terraform', 'MongoDB', 'PostgreSQL', 'Elasticsearch',
]

const projectContexts = [
  'Proyek pribadi',
  'Proyek kampus/bootcamp',
  'Proyek produksi (pengguna nyata)',
  'Proyek lintas bidang/industri',
]

const courseDurations = [
  'Singkat (kurang dari 2 jam)',
  'Sedang (2–6 jam)',
  'Panjang (lebih dari 6 jam)',
  'Durasi apa pun',
]

const paymentOptions = ['Berbayar', 'Gratis', 'Keduanya (Berbayar dan Gratis)']

export function countSelectedTechnologies(answer: ProfileQuestionAnswer) {
  const customTechnologies = answer.otherTechnologies
    .split(',')
    .map((technology) => technology.trim())
    .filter(Boolean)
  return new Set([...answer.technologies, ...customTechnologies].map((technology) => technology.toLocaleLowerCase())).size
}

export function isProfileQuestionAnswered(questionIndex: number, answer: ProfileQuestionAnswer) {
  if (questionIndex === 6) return answer.projectCount !== '' && Number(answer.projectCount) >= 0
  if (questionIndex === 7) {
    const count = countSelectedTechnologies(answer)
    return count >= 2
  }
  if (questionIndex === 8) return Boolean(answer.duration)
  if (questionIndex === 9) return Boolean(answer.payment)
  return false
}

export function ProfileQuestionFields({
  questionNumber,
  value,
  onChange,
}: {
  questionNumber: number
  value: ProfileQuestionAnswer
  onChange: (value: ProfileQuestionAnswer) => void
}) {
  const selectedTechnologyCount = countSelectedTechnologies(value)

  if (questionNumber === 7) {
    return (
      <div className="profile-question-fields">
        <div className="profile-question-field">
          <label htmlFor="profile-project-count">Jumlah proyek yang pernah dikerjakan</label>
          <input
            id="profile-project-count"
            type="number"
            min={0}
            step={1}
            inputMode="numeric"
            placeholder="Contoh: 5"
            value={value.projectCount}
            onChange={(event: ChangeEvent<HTMLInputElement>) => {
              const nextValue = event.target.value
              if (nextValue === '' || /^\d+$/.test(nextValue)) onChange({ ...value, projectCount: nextValue })
            }}
          />
        </div>

        <fieldset className="profile-question-field profile-context-fieldset">
          <legend>Pilih semua konteks proyek yang pernah Anda tangani</legend>
          <div className="profile-checkbox-grid">
            {projectContexts.map((context) => (
              <label className="profile-checkbox-option" key={context}>
                <input
                  type="checkbox"
                  checked={value.projectContexts.includes(context)}
                  onChange={(event) => {
                    const nextContexts = event.target.checked
                      ? [...value.projectContexts, context]
                      : value.projectContexts.filter((item) => item !== context)
                    onChange({ ...value, projectContexts: nextContexts })
                  }}
                />
                <span>{context}</span>
              </label>
            ))}
          </div>
        </fieldset>
      </div>
    )
  }

  if (questionNumber === 8) {
    const textItems = value.otherTechnologies.split(',').map((technology) => technology.trim()).filter(Boolean)
    const normalizedItems = new Map<string, string>()
    for (const item of [...textItems, ...value.technologies]) {
      const normalized = item.toLocaleLowerCase()
      if (!normalizedItems.has(normalized)) normalizedItems.set(normalized, item)
    }
    const selectedItems = [...normalizedItems.values()]
    const selectedKeys = new Set(selectedItems.map((technology) => technology.toLocaleLowerCase()))
    const missingQuickPicks = value.technologies.filter((technology) => !textItems.some((item) => item.toLocaleLowerCase() === technology.toLocaleLowerCase()))
    const technologyText = missingQuickPicks.length
      ? [...missingQuickPicks, value.otherTechnologies].filter(Boolean).join(', ')
      : value.otherTechnologies

    const updateTechnologyItems = (items: string[]) => {
      const uniqueItems = [...new Map(items.map((item) => [item.toLocaleLowerCase(), item.trim()])).values()].filter(Boolean)
      const selectedQuickPicks = quickTechnologies.filter((technology) => uniqueItems.some((item) => item.toLocaleLowerCase() === technology.toLocaleLowerCase()))
      onChange({ ...value, technologies: selectedQuickPicks, otherTechnologies: uniqueItems.join(', ') })
    }

    return (
      <div className="profile-question-fields">
        <div className="profile-question-field">
          <label htmlFor="profile-other-technologies">Jawaban teknologi/tools Anda</label>
          <textarea
            id="profile-other-technologies"
            rows={4}
            placeholder="Contoh: Docker, AWS, Kubernetes, dan teknologi lainnya"
            value={technologyText}
            aria-describedby="profile-technology-guidance"
            onChange={(event: ChangeEvent<HTMLTextAreaElement>) => {
              const nextText = event.target.value
              const nextItems = nextText.split(',').map((technology) => technology.trim()).filter(Boolean)
              const selectedQuickPicks = quickTechnologies.filter((technology) => nextItems.some((item) => item.toLocaleLowerCase() === technology.toLocaleLowerCase()))
              onChange({ ...value, technologies: selectedQuickPicks, otherTechnologies: nextText })
            }}
          />
          <small id="profile-technology-guidance">
            Pisahkan teknologi dengan koma. Pilih minimal 2 teknologi, tanpa batas jumlah.
          </small>
        </div>

        <fieldset className="profile-question-field profile-technology-fieldset">
          <legend>Pilihan teknologi cepat</legend>
          <div className="technology-quick-picks">
            {quickTechnologies.map((technology) => {
              const selected = selectedKeys.has(technology.toLocaleLowerCase())
              return (
                <button
                  type="button"
                  className={`technology-chip${selected ? ' selected' : ''}`}
                  key={technology}
                  aria-pressed={selected}
                  onClick={() => {
                    const nextItems = selected
                      ? selectedItems.filter((item) => item.toLocaleLowerCase() !== technology.toLocaleLowerCase())
                      : [...selectedItems, technology]
                    updateTechnologyItems(nextItems)
                  }}
                >
                  {technology}
                </button>
              )
            })}
          </div>
          <p className="technology-selection-count" role="status" aria-live="polite">
            {selectedTechnologyCount} teknologi dipilih
          </p>
        </fieldset>
      </div>
    )
  }

  const options = questionNumber === 9 ? courseDurations : paymentOptions
  const selectedValue = questionNumber === 9 ? value.duration : value.payment
  const fieldName = questionNumber === 9 ? 'profile-duration' : 'profile-payment'

  return (
    <fieldset className="profile-question-fields profile-card-fieldset">
      <legend className="sr-only">{questionNumber === 9 ? 'Pilih durasi kursus' : 'Pilih preferensi pembayaran'}</legend>
      <div className="profile-choice-grid">
        {options.map((option) => {
          const selected = selectedValue === option
          return (
            <label className={`profile-choice-card${selected ? ' selected' : ''}`} key={option}>
              <input
                type="radio"
                name={fieldName}
                value={option}
                checked={selected}
                onChange={() => onChange(questionNumber === 9 ? { ...value, duration: option } : { ...value, payment: option })}
              />
              <span>{option}</span>
            </label>
          )
        })}
      </div>
    </fieldset>
  )
}
