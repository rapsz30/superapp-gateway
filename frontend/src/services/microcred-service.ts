import { apiFetch } from '@/src/lib/api'

export interface Track {
  slug: string
  name: string
  description?: string | null
  question_count: number
}

export interface QuestionOption {
  id: string
  text: string
}

export interface AssessmentQuestion {
  id: string
  sequence: number
  question_type: 'theoretical' | 'essay' | 'profile' | string
  prompt: string
  difficulty?: string | null
  options?: unknown
  metadata?: Record<string, unknown> | null
  expected_values?: Record<string, unknown> | null
  response?: Record<string, unknown> | null
}

export interface AssessmentStart {
  assessment_id: string
  status: string
  expires_at?: string | null
  role: Track
  questions: AssessmentQuestion[]
}

export interface AnswerPayload {
  question_id: string
  answer_text?: string
  selected_option?: string
  selected_option_id?: string
  selected_options?: string[]
  project_count?: number
  project_contexts?: string[]
}

export interface AssessmentStatus {
  assessment_id: string
  status: string
  overall_progress: number
  degraded: boolean
  stages: { name: string; status: string; percentage: number }[]
}

export interface RecommendedCourse {
  rank: number
  course_id: string
  course_title: string
  course_url?: string | null
  relevance_score: number
  match_reason?: string | null
  metadata?: Record<string, unknown> | null
}

export interface AssessmentResult {
  assessment_id: string
  status: string
  completed: boolean
  summary?: string | null
  overall_score?: number | null
  score_breakdown?: {
    theoretical?: Record<string, unknown> | null
    profile?: Record<string, unknown> | null
    essay?: Record<string, unknown> | null
    overall?: Record<string, unknown> | null
  } | null
  recommendations: RecommendedCourse[]
  degraded?: boolean
  message?: string | null
}

const base = '/api/micro-cred'

export const microcredService = {
  async tracks(): Promise<Track[]> {
    const result = await apiFetch<{ tracks: Track[] }>(`${base}/tracks`)
    return result.tracks ?? []
  },

  start(roleSlug: string): Promise<AssessmentStart> {
    return apiFetch<AssessmentStart>(`${base}/assessments/start`, { method: 'POST', json: { role_slug: roleSlug } })
  },

  async abandon(assessmentId: string): Promise<void> {
    await apiFetch(`${base}/assessments/${assessmentId}/abandon`, { method: 'DELETE' })
  },

  submit(assessmentId: string, responses: AnswerPayload[]) {
    return apiFetch<{ assessment_id: string; status: string }>(`${base}/assessments/${assessmentId}/submit`, {
      method: 'POST',
      json: { responses },
    })
  },

  status(assessmentId: string): Promise<AssessmentStatus> {
    return apiFetch<AssessmentStatus>(`${base}/assessments/${assessmentId}/status`)
  },

  result(assessmentId: string): Promise<AssessmentResult> {
    return apiFetch<AssessmentResult>(`${base}/assessments/${assessmentId}/result`)
  },

  emailSummary(assessmentId: string): Promise<{ to_email: string; sent_at: string }> {
    return apiFetch(`${base}/assessments/${assessmentId}/email-summary`, { method: 'POST' })
  },
}
