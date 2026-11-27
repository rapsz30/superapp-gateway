'use client'

import type { ChangeEvent } from 'react'
import type { AssessmentQuestion, QuestionOption } from '@/src/services/microcred-service'

export type ProfileAnswerState = {
  projectCount: string
  selectedValues: string[]
  otherText: string
  selectedOption: string
}

export const emptyProfileAnswerState: ProfileAnswerState = {
  projectCount: '',
  selectedValues: [],
  otherText: '',
  selectedOption: '',
}

export function normalizeOptions(raw: unknown): QuestionOption[] {
  if (!Array.isArray(raw)) return []
  return raw
    .map((opt, i) => {
      if (typeof opt === 'string') return { id: String.fromCharCode(65 + i), text: opt }
      if (opt && typeof opt === 'object') {
        const rec = opt as Record<string, unknown>
        const id = String(rec.id ?? rec.key ?? String.fromCharCode(65 + i))
        const text = String(rec.text ?? rec.label ?? rec.value ?? id)
        return { id, text }
      }
      return null
    })
    .filter((item): item is QuestionOption => item !== null)
}

export function isProfileQuestionAnswered(q: AssessmentQuestion, state: ProfileAnswerState): boolean {
  const captures = Array.isArray(q.metadata?.captures) ? (q.metadata?.captures as string[]) : []
  const accepted = Array.isArray(q.metadata?.accepted_values) ? (q.metadata?.accepted_values as string[]) : []
  const opts = normalizeOptions(q.options)

  if (captures.includes('project_count')) {
    return state.projectCount !== '' && Number(state.projectCount) >= 0
  }
  if (opts.length === 0 && accepted.length > 0) {
    const textItems = state.otherText.split(',').map((s) => s.trim()).filter(Boolean)
    return new Set([...state.selectedValues, ...textItems].map((v) => v.toLowerCase())).size > 0
  }
  if (opts.length > 0) return Boolean(state.selectedOption)
  return Boolean(state.otherText.trim())
}

export function ProfileQuestionFields({
  question,
  value,
  onChange,
}: {
  question: AssessmentQuestion
  value: ProfileAnswerState
  onChange: (value: ProfileAnswerState) => void
}) {
  const captures = Array.isArray(question.metadata?.captures) ? (question.metadata?.captures as string[]) : []
  const accepted = Array.isArray(question.metadata?.accepted_values) ? (question.metadata?.accepted_values as string[]) : []
  const opts = normalizeOptions(question.options)

  if (captures.includes('project_count')) {
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

        {accepted.length > 0 && (
          <fieldset className="profile-question-field profile-context-fieldset">
            <legend>Pilih semua konteks proyek yang pernah Anda tangani</legend>
            <div className="profile-checkbox-grid">
              {accepted.map((context) => (
                <label className="profile-checkbox-option" key={context}>
                  <input
                    type="checkbox"
                    checked={value.selectedValues.includes(context)}
                    onChange={(event) => {
                      const nextContexts = event.target.checked
                        ? [...value.selectedValues, context]
                        : value.selectedValues.filter((item) => item !== context)
                      onChange({ ...value, selectedValues: nextContexts })
                    }}
                  />
                  <span>{context}</span>
                </label>
              ))}
            </div>
          </fieldset>
        )}
      </div>
    )
  }

  if (opts.length === 0 && accepted.length > 0) {
    const textItems = value.otherText.split(',').map((s) => s.trim()).filter(Boolean)
    const normalizedItems = new Map<string, string>()
    for (const item of [...textItems, ...value.selectedValues]) {
      const key = item.toLocaleLowerCase()
      if (!normalizedItems.has(key)) normalizedItems.set(key, item)
    }
    const selectedItems = [...normalizedItems.values()]
    const selectedKeys = new Set(selectedItems.map((s) => s.toLocaleLowerCase()))
    const missingQuickPicks = value.selectedValues.filter((t) => !textItems.some((item) => item.toLocaleLowerCase() === t.toLocaleLowerCase()))
    const displayText = missingQuickPicks.length ? [...missingQuickPicks, value.otherText].filter(Boolean).join(', ') : value.otherText

    const updateItems = (items: string[]) => {
      const uniqueItems = [...new Map(items.map((item) => [item.toLocaleLowerCase(), item.trim()])).values()].filter(Boolean)
      const selectedQuickPicks = accepted.filter((tech) => uniqueItems.some((item) => item.toLocaleLowerCase() === tech.toLocaleLowerCase()))
      onChange({ ...value, selectedValues: selectedQuickPicks, otherText: uniqueItems.join(', ') })
    }

    return (
      <div className="profile-question-fields">
        <div className="profile-question-field">
          <label htmlFor="profile-other-technologies">Jawaban teknologi/tools Anda</label>
          <textarea
            id="profile-other-technologies"
            rows={4}
            placeholder="Contoh: Docker, AWS, Kubernetes, dan teknologi lainnya"
            value={displayText}
            aria-describedby="profile-technology-guidance"
            onChange={(event: ChangeEvent<HTMLTextAreaElement>) => {
              const nextText = event.target.value
              const nextItems = nextText.split(',').map((t) => t.trim()).filter(Boolean)
              const selectedQuickPicks = accepted.filter((tech) => nextItems.some((item) => item.toLocaleLowerCase() === tech.toLocaleLowerCase()))
              onChange({ ...value, selectedValues: selectedQuickPicks, otherText: nextText })
            }}
          />
          <small id="profile-technology-guidance">Pisahkan dengan koma atau pilih cepat dari daftar di bawah.</small>
        </div>

        <fieldset className="profile-question-field profile-technology-fieldset">
          <legend>Pilihan cepat</legend>
          <div className="technology-quick-picks">
            {accepted.map((tech) => {
              const selected = selectedKeys.has(tech.toLocaleLowerCase())
              return (
                <button
                  type="button"
                  className={`technology-chip${selected ? ' selected' : ''}`}
                  key={tech}
                  aria-pressed={selected}
                  onClick={() => {
                    const nextItems = selected
                      ? selectedItems.filter((item) => item.toLocaleLowerCase() !== tech.toLocaleLowerCase())
                      : [...selectedItems, tech]
                    updateItems(nextItems)
                  }}
                >
                  {tech}
                </button>
              )
            })}
          </div>
          <p className="technology-selection-count" role="status" aria-live="polite">
            {selectedItems.length} item dipilih
          </p>
        </fieldset>
      </div>
    )
  }

  if (opts.length > 0) {
    return (
      <fieldset className="profile-question-fields profile-card-fieldset">
        <legend className="sr-only">Pilih salah satu opsi</legend>
        <div className="profile-choice-grid">
          {opts.map((option) => {
            const selected = value.selectedOption === option.id
            return (
              <label className={`profile-choice-card${selected ? ' selected' : ''}`} key={option.id}>
                <input
                  type="radio"
                  name={`profile-choice-${question.id}`}
                  value={option.id}
                  checked={selected}
                  onChange={() => onChange({ ...value, selectedOption: option.id })}
                />
                <span>{option.text}</span>
              </label>
            )
          })}
        </div>
      </fieldset>
    )
  }

  return (
    <div className="profile-question-fields">
      <div className="profile-question-field">
        <label htmlFor={`profile-text-${question.id}`}>Jawaban Anda</label>
        <textarea
          id={`profile-text-${question.id}`}
          rows={4}
          value={value.otherText}
          placeholder="Tulis jawaban Anda di sini..."
          onChange={(event) => onChange({ ...value, otherText: event.target.value })}
        />
      </div>
    </div>
  )
}
