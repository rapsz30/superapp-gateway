'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { AlertCircle, Brain, CheckCircle2, Clock3, Database, Layers, Loader2, RotateCcw, WifiOff } from 'lucide-react'
import { errorMessage } from '@/src/lib/api'
import { microcredService, type AnswerPayload, type AssessmentResult } from '@/src/services/microcred-service'

export type PipelineStageId = 'gpt' | 'rag' | 'fusion'
export type PipelineStageStatus = 'queued' | 'in-progress' | 'complete' | 'failed'

const pipelineStages: { id: PipelineStageId; title: string }[] = [
  { id: 'gpt', title: 'GPT Scoring' },
  { id: 'rag', title: 'RAG Retrieval' },
  { id: 'fusion', title: 'Fusion Summary' },
]

type StageState = { status: PipelineStageStatus; progress: number; error?: string }

const stageIcons: Record<PipelineStageId, typeof Brain> = {
  gpt: Brain,
  rag: Database,
  fusion: Layers,
}

const statusLabels: Record<PipelineStageStatus, string> = {
  queued: 'Queued',
  'in-progress': 'In Progress',
  complete: 'Complete',
  failed: 'Gagal',
}

const initialStages = () =>
  Object.fromEntries(pipelineStages.map((stage) => [stage.id, { status: 'queued', progress: 0 }])) as Record<PipelineStageId, StageState>

function formatElapsed(totalSeconds: number) {
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
}

function mapStageStatus(raw: string | undefined): PipelineStageStatus {
  if (raw === 'completed' || raw === 'complete') return 'complete'
  if (raw === 'in_progress' || raw === 'in-progress') return 'in-progress'
  if (raw === 'failed') return 'failed'
  return 'queued'
}

export function AssessmentProcessing({
  track,
  assessmentId,
  responses,
  onViewResult,
  onBackToQuestions,
}: {
  track: string
  assessmentId: string
  responses: AnswerPayload[]
  onViewResult: (result: AssessmentResult) => void
  onBackToQuestions: (message: string) => void
}) {
  const [stages, setStages] = useState(initialStages)
  const [overallProgress, setOverallProgress] = useState(0)
  const [result, setResult] = useState<AssessmentResult | null>(null)
  const [runId, setRunId] = useState(0)
  const [elapsed, setElapsed] = useState(0)
  const [isOffline, setIsOffline] = useState(false)
  const startedAt = useRef<number | null>(null)
  const submittedRef = useRef(false)

  const isComplete = result !== null && pipelineStages.every((stage) => stages[stage.id].status === 'complete')
  const hasFailed = pipelineStages.some((stage) => stages[stage.id].status === 'failed')

  useEffect(() => {
    if (startedAt.current === null) startedAt.current = Date.now()
    if (isComplete) return
    const tick = () => setElapsed(Math.floor((Date.now() - (startedAt.current ?? Date.now())) / 1000))
    tick()
    const interval = setInterval(tick, 1000)
    return () => clearInterval(interval)
  }, [isComplete])

  useEffect(() => {
    const update = () => setIsOffline(!navigator.onLine)
    update()
    window.addEventListener('online', update)
    window.addEventListener('offline', update)
    return () => {
      window.removeEventListener('online', update)
      window.removeEventListener('offline', update)
    }
  }, [])

  useEffect(() => {
    let active = true

    async function run() {
      try {
        if (!submittedRef.current) {
          await microcredService.submit(assessmentId, responses)
          submittedRef.current = true
        }
        if (!active) return

        for (let attempt = 0; attempt < 90; attempt += 1) {
          if (!active) return
          const st = await microcredService.status(assessmentId)
          if (!active) return

          const nextStages = initialStages()
          for (const stage of st.stages ?? []) {
            if (stage.name === 'gpt' || stage.name === 'rag' || stage.name === 'fusion') {
              const mapped = mapStageStatus(stage.status)
              nextStages[stage.name] = {
                status: mapped,
                progress: mapped === 'complete' ? 100 : Math.round(stage.percentage ?? 0),
              }
            }
          }

          if (st.status === 'completed') {
            for (const s of pipelineStages) {
              nextStages[s.id] = { status: 'complete', progress: 100 }
            }
            setStages(nextStages)
            setOverallProgress(100)
            const finalResult = await microcredService.result(assessmentId)
            if (active) setResult(finalResult)
            return
          }

          setStages(nextStages)
          setOverallProgress(Math.min(99, Math.max(5, Math.round(st.overall_progress ?? 0))))

          if (st.status === 'failed') {
            setStages((prev) => ({
              ...prev,
              fusion: { status: 'failed', progress: prev.fusion.progress, error: 'Pemrosesan asesmen di server gagal.' },
            }))
            return
          }

          await new Promise((resolve) => window.setTimeout(resolve, 1500))
        }

        if (active) {
          setStages((prev) => ({
            ...prev,
            fusion: { status: 'failed', progress: prev.fusion.progress, error: 'Waktu tunggu pemrosesan habis.' },
          }))
        }
      } catch (caught) {
        if (!active) return
        const msg = errorMessage(caught, 'Gagal mengirim jawaban asesmen.')
        if (!submittedRef.current) {
          onBackToQuestions(msg)
          return
        }
        setStages((prev) => ({
          ...prev,
          fusion: { status: 'failed', progress: prev.fusion.progress, error: msg },
        }))
      }
    }

    run()
    return () => {
      active = false
    }
  }, [assessmentId, responses, runId, onBackToQuestions])

  const retry = useCallback(() => setRunId((id) => id + 1), [])

  return (
    <div className="page-content processing-page">
      <header className="processing-header">
        <div>
          <span className="processing-eyebrow">{track}</span>
          <h1>Memproses Asesmen</h1>
          <p>Jawaban Anda sedang dianalisis. Halaman ini akan diperbarui otomatis, mohon tidak menutup halaman.</p>
        </div>
        <div className="processing-timer" role="timer" aria-label={`Durasi proses ${formatElapsed(elapsed)}`}>
          <Clock3 aria-hidden="true" />
          <div><span>Durasi proses</span><b>{formatElapsed(elapsed)}</b></div>
        </div>
      </header>

      <section className="processing-overall" aria-labelledby="overall-progress-label">
        <div className="processing-overall-head">
          <h2 id="overall-progress-label">Overall Progress</h2>
          <b>{overallProgress}%</b>
        </div>
        <div className="processing-bar large" role="progressbar" aria-labelledby="overall-progress-label" aria-valuemin={0} aria-valuemax={100} aria-valuenow={overallProgress}>
          <span className={isComplete ? 'complete' : ''} style={{ width: `${overallProgress}%` }} />
        </div>
        <p className="processing-overall-note" aria-live="polite">
          {isComplete
            ? 'Semua proses selesai. Hasil asesmen Anda siap dilihat.'
            : hasFailed
              ? 'Proses terhenti. Silakan coba lagi.'
              : `${pipelineStages.filter((stage) => stages[stage.id].status === 'complete').length} dari ${pipelineStages.length} tahap selesai`}
        </p>
      </section>

      {isOffline && (
        <div className="processing-alert" role="alert">
          <WifiOff aria-hidden="true" />
          <span>Koneksi internet terputus. Proses akan gagal jika koneksi tidak kembali.</span>
        </div>
      )}

      <ol className="processing-stages">
        {pipelineStages.map((stage) => {
          const state = stages[stage.id]
          const Icon = stageIcons[stage.id]
          return (
            <li key={stage.id} className={`processing-stage ${state.status}`}>
              <div className="processing-stage-icon" aria-hidden="true">
                {state.status === 'complete' ? (
                  <CheckCircle2 />
                ) : state.status === 'in-progress' ? (
                  <Loader2 className="spin" />
                ) : state.status === 'failed' ? (
                  <AlertCircle />
                ) : (
                  <Icon />
                )}
              </div>
              <div className="processing-stage-body">
                <div className="processing-stage-head">
                  <h3>{stage.title}</h3>
                  <span className="processing-status">{statusLabels[state.status]}</span>
                </div>
                {state.status === 'failed' && <p>{state.error}</p>}
                {state.status === 'in-progress' && (
                  <div className="processing-stage-progress">
                    <div className="processing-bar" role="progressbar" aria-label={`Progres ${stage.title}`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={state.progress}>
                      <span style={{ width: `${state.progress}%` }} />
                    </div>
                    <b>{state.progress}%</b>
                  </div>
                )}
                {state.status === 'failed' && (
                  <button type="button" className="outline-button processing-retry" onClick={retry}>
                    <RotateCcw aria-hidden="true" />
                    Coba lagi
                  </button>
                )}
              </div>
            </li>
          )
        })}
      </ol>

      <div className="processing-actions">
        <button
          type="button"
          className="primary"
          disabled={!isComplete || !result}
          aria-disabled={!isComplete || !result}
          onClick={() => result && onViewResult(result)}
        >
          Lihat hasil
        </button>
      </div>
    </div>
  )
}
