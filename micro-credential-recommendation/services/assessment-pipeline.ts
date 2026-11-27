export type PipelineStageId = 'gpt-scoring' | 'rag-retrieval' | 'fusion-summary'
export type PipelineStageStatus = 'queued' | 'in-progress' | 'complete' | 'failed'

export type PipelineStage = {
  id: PipelineStageId
  title: string
}

export const pipelineStages: PipelineStage[] = [
  { id: 'gpt-scoring', title: 'GPT Scoring' },
  { id: 'rag-retrieval', title: 'RAG Retrieval' },
  { id: 'fusion-summary', title: 'Fusion Summary' },
]

type RunStageOptions = {
  signal: AbortSignal
  onProgress: (progress: number) => void
}

const stageDurations: Record<PipelineStageId, number> = {
  'gpt-scoring': 4200,
  'rag-retrieval': 3600,
  'fusion-summary': 3000,
}

function wait(ms: number, signal: AbortSignal) {
  return new Promise<void>((resolve, reject) => {
    if (signal.aborted) return reject(new DOMException('Aborted', 'AbortError'))
    const timeout = setTimeout(resolve, ms)
    signal.addEventListener('abort', () => { clearTimeout(timeout); reject(new DOMException('Aborted', 'AbortError')) }, { once: true })
  })
}

/**
 * The project has no assessment processing API yet, so each stage runs locally.
 * Replace the body with the backend call (e.g. polling a job status endpoint)
 * once it exists; callers only depend on onProgress and the resolved/rejected promise.
 */
export async function runPipelineStage(stageId: PipelineStageId, { signal, onProgress }: RunStageOptions) {
  const steps = 20
  const stepDuration = stageDurations[stageId] / steps
  for (let step = 1; step <= steps; step += 1) {
    await wait(stepDuration, signal)
    if (typeof navigator !== 'undefined' && !navigator.onLine) throw new Error('Koneksi internet terputus.')
    onProgress(Math.round((step / steps) * 100))
  }
}
