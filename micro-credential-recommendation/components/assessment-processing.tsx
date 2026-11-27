'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { AlertCircle, Brain, CheckCircle2, Clock3, Database, Layers, Loader2, RotateCcw, WifiOff } from 'lucide-react'
import { pipelineStages, runPipelineStage, type PipelineStageId, type PipelineStageStatus } from '@/features/micro-credential-recommendation/services/assessment-pipeline'

type StageState = { status: PipelineStageStatus; progress: number; error?: string }

const stageIcons: Record<PipelineStageId, typeof Brain> = {
  'gpt-scoring': Brain,
  'rag-retrieval': Database,
  'fusion-summary': Layers,
}

const statusLabels: Record<PipelineStageStatus, string> = {
  queued: 'Queued',
  'in-progress': 'In Progress',
  complete: 'Complete',
  failed: 'Gagal',
}

const initialStages = () => Object.fromEntries(pipelineStages.map((stage) => [stage.id, { status: 'queued', progress: 0 }])) as Record<PipelineStageId, StageState>

function formatElapsed(totalSeconds: number) {
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
}

export function AssessmentProcessing({ track, onViewResult }: { track: string; onViewResult: () => void }) {
  const [stages, setStages] = useState(initialStages)
  const [runId, setRunId] = useState(0)
  const [elapsed, setElapsed] = useState(0)
  const [isOffline, setIsOffline] = useState(false)
  const startedAt = useRef<number | null>(null)

  const isComplete = pipelineStages.every((stage) => stages[stage.id].status === 'complete')
  const hasFailed = pipelineStages.some((stage) => stages[stage.id].status === 'failed')
  const overallProgress = isComplete ? 100 : Math.min(99, Math.floor(pipelineStages.reduce((sum, stage) => sum + stages[stage.id].progress, 0) / pipelineStages.length))

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
    return () => { window.removeEventListener('online', update); window.removeEventListener('offline', update) }
  }, [])

  const stagesRef = useRef(stages)
  stagesRef.current = stages

  useEffect(() => {
    const controller = new AbortController()
    const setStage = (id: PipelineStageId, next: Partial<StageState>) => setStages((current) => ({ ...current, [id]: { ...current[id], ...next } }))

    async function run() {
      for (const stage of pipelineStages) {
        if (stagesRef.current[stage.id].status === 'complete') continue
        setStage(stage.id, { status: 'in-progress', progress: 0, error: undefined })
        try {
          await runPipelineStage(stage.id, { signal: controller.signal, onProgress: (progress) => setStage(stage.id, { progress }) })
          if (controller.signal.aborted) return
          setStage(stage.id, { status: 'complete', progress: 100 })
        } catch (error) {
          if (controller.signal.aborted) return
          setStage(stage.id, { status: 'failed', error: error instanceof Error ? error.message : 'Terjadi kesalahan saat memproses.' })
          return
        }
      }
    }

    run()
    return () => controller.abort()
  }, [runId])

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
          {isComplete ? 'Semua proses selesai. Hasil asesmen Anda siap dilihat.' : hasFailed ? 'Proses terhenti. Silakan coba lagi.' : `${pipelineStages.filter((stage) => stages[stage.id].status === 'complete').length} dari ${pipelineStages.length} tahap selesai`}
        </p>
      </section>

      {isOffline && <div className="processing-alert" role="alert"><WifiOff aria-hidden="true" /><span>Koneksi internet terputus. Proses akan gagal jika koneksi tidak kembali.</span></div>}

      <ol className="processing-stages">
        {pipelineStages.map((stage) => {
          const state = stages[stage.id]
          const Icon = stageIcons[stage.id]
          return (
            <li key={stage.id} className={`processing-stage ${state.status}`}>
              <div className="processing-stage-icon" aria-hidden="true">
                {state.status === 'complete' ? <CheckCircle2 /> : state.status === 'in-progress' ? <Loader2 className="spin" /> : state.status === 'failed' ? <AlertCircle /> : <Icon />}
              </div>
              <div className="processing-stage-body">
                <div className="processing-stage-head">
                  <h3>{stage.title}</h3>
                  <span className="processing-status">{statusLabels[state.status]}</span>
                </div>
                {state.status === 'failed' && <p>{state.error}</p>}
                {state.status === 'in-progress' && (
                  <div className="processing-stage-progress">
                    <div className="processing-bar" role="progressbar" aria-label={`Progres ${stage.title}`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={state.progress}><span style={{ width: `${state.progress}%` }} /></div>
                    <b>{state.progress}%</b>
                  </div>
                )}
                {state.status === 'failed' && <button type="button" className="outline-button processing-retry" onClick={retry}><RotateCcw aria-hidden="true" />Coba lagi</button>}
              </div>
            </li>
          )
        })}
      </ol>

      <div className="processing-actions">
        <button type="button" className="primary" disabled={!isComplete} aria-disabled={!isComplete} onClick={onViewResult}>
          Lihat hasil
        </button>
      </div>
    </div>
  )
}
