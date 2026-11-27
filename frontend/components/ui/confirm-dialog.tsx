'use client'

import { useEffect, useRef, type ReactNode } from 'react'
import { AlertTriangle, X } from 'lucide-react'

type ConfirmDialogProps = {
  open: boolean
  title: string
  description: ReactNode
  confirmLabel: string
  tone?: 'danger' | 'primary'
  onCancel: () => void
  onConfirm: () => void | Promise<void>
}

export function ConfirmDialog({ open, title, description, confirmLabel, tone = 'primary', onCancel, onConfirm }: ConfirmDialogProps) {
  const dialogRef = useRef<HTMLDivElement>(null)
  const onCancelRef = useRef(onCancel)
  onCancelRef.current = onCancel

  useEffect(() => {
    if (!open) return
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null
    const dialog = dialogRef.current
    const focusable = (): HTMLElement[] => dialog ? Array.from(dialog.querySelectorAll<HTMLElement>('button:not(:disabled), [href], input:not(:disabled), [tabindex]:not([tabindex="-1"])')) : [];
    (focusable().find((item) => item.dataset.dialogInitial !== undefined) ?? focusable()[0])?.focus()

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        event.preventDefault()
        onCancelRef.current()
        return
      }
      if (event.key !== 'Tab') return
      const items = focusable()
      if (!items.length) return
      const first = items[0]
      const last = items[items.length - 1]
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      if (previousFocus?.isConnected) previousFocus.focus()
    }
  }, [open])

  if (!open) return null

  return <div className="dialog-backdrop action-confirm-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onCancel() }}>
    <div ref={dialogRef} className="action-confirm-dialog" role="alertdialog" aria-modal="true" aria-labelledby="action-confirm-title" aria-describedby="action-confirm-description" tabIndex={-1}>
      <button type="button" className="action-confirm-close" aria-label="Tutup dialog" onClick={onCancel}><X /></button>
      <div className={`action-confirm-icon ${tone}`}><AlertTriangle aria-hidden="true" /></div>
      <h2 id="action-confirm-title">{title}</h2>
      <div id="action-confirm-description" className="action-confirm-description">{description}</div>
      <div className="action-confirm-actions">
        <button type="button" className="outline-button" data-dialog-initial onClick={onCancel}>Batal</button>
        <button type="button" className={`action-confirm-submit ${tone}`} onClick={() => void onConfirm()}>{confirmLabel}</button>
      </div>
    </div>
  </div>
}
