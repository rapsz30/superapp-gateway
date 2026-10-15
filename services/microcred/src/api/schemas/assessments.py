from __future__ import annotations

from typing import Any

from pydantic import AnyHttpUrl, BaseModel, EmailStr, Field
from src.api.schemas.tracks import TrackItem


class AssessmentStartRequest(BaseModel):
    role_slug: str = Field(..., description="Role/track identifier to start or resume")


class AssessmentQuestionOption(BaseModel):
    """Option for multiple choice questions"""

    id: str = Field(..., description="Option identifier (A, B, C, D)")
    text: str = Field(..., description="Option text")


class AssessmentQuestion(BaseModel):
    id: str
    sequence: int
    question_type: str
    prompt: str
    difficulty: str | None = Field(None, description="Question difficulty: easy, medium, hard")
    options: Any = Field(
        None,
        description="Options - list for MC, dict for compound, null for essay",
    )
    metadata: dict | None = None
    expected_values: dict | None = Field(
        None, description="Expected values and validation rules for profile questions"
    )
    response: dict | None = None


class AssessmentStartResponse(BaseModel):
    assessment_id: str
    status: str
    expires_at: str | None = Field(None, description="ISO timestamp when assessment expires")
    role: TrackItem
    questions: list[AssessmentQuestion]


# Story 2.1: Submission request schema
class AssessmentResponsePayload(BaseModel):
    question_id: str
    answer_text: str | None = None
    selected_option: str | None = None
    selected_option_id: str | None = None
    value: Any = None
    selected_options: list[str] | None = None
    project_count: int | str | None = None
    project_contexts: list[str] | None = None
    metadata: dict | None = None


class AssessmentSubmitRequest(BaseModel):
    responses: list[AssessmentResponsePayload] = Field(
        default_factory=list,
        description="Student responses collected on the client",
    )


# Story 2.1: Submission schemas
class ScoreBreakdownItem(BaseModel):
    question_id: str
    score: float
    max_score: float
    explanation: str | None = None


class ScoreTypeDetail(BaseModel):
    total: float = 0.0
    max: float = 0.0
    count: int = 0
    percentage: float = 0.0
    breakdown: list[ScoreBreakdownItem] = []


class EssayScoreStatus(BaseModel):
    count: int = 0
    status: str = "pending_gpt"


class SubmissionScores(BaseModel):
    theoretical: ScoreTypeDetail
    profile: ScoreTypeDetail
    essay: EssayScoreStatus


class AssessmentSubmitResponse(BaseModel):
    assessment_id: str
    status: str
    submitted_at: str
    degraded: bool = Field(False, description="True if submission had missing or incomplete data")
    scores: SubmissionScores
    jobs_queued: list[str] = Field(
        default_factory=list, description="Async job types queued (gpt, rag, fusion)"
    )


# Story 2.3: Status polling schemas
class JobProgress(BaseModel):
    """Progress of a single async job."""

    job_type: str = Field(..., description="Job type: gpt, rag, or fusion")
    status: str = Field(..., description="Job status: queued, in_progress, completed, failed")
    attempts: int = Field(0, description="Number of attempts made")
    max_attempts: int = Field(3, description="Maximum attempts allowed")
    started_at: str | None = Field(None, description="ISO timestamp when job started")
    completed_at: str | None = Field(None, description="ISO timestamp when job completed")
    error: str | None = Field(None, description="Error message if failed")
    progress_percentage: float | None = Field(
        None, description="Real-time job progress percentage (0-100)"
    )
    progress_step: str | None = Field(None, description="Current processing step label")


class StageProgress(BaseModel):
    """Progress of a processing stage."""

    name: str = Field(..., description="Stage name: rule_score, gpt, rag, fusion")
    status: str = Field(..., description="Stage status: pending, in_progress, completed, failed")
    percentage: float = Field(0.0, description="Completion percentage (0-100)")


class AssessmentStatusResponse(BaseModel):
    """Response for GET /assessments/{id}/status endpoint."""

    assessment_id: str
    status: str = Field(
        ..., description="Assessment status: in_progress, submitted, completed, failed"
    )
    submitted_at: str | None = Field(None, description="ISO timestamp when submitted")
    completed_at: str | None = Field(None, description="ISO timestamp when all jobs completed")
    degraded: bool = Field(False, description="True if submission had issues")
    overall_progress: float = Field(
        0.0, description="Overall completion percentage across all stages (0-100)"
    )
    stages: list[StageProgress] = Field(
        default_factory=list, description="Progress of each processing stage"
    )
    jobs: list[JobProgress] = Field(default_factory=list, description="Status of async jobs")
    webhook_url: str | None = Field(None, description="Registered webhook URL for callbacks")


# Story 2.3: Webhook registration
class WebhookRegisterRequest(BaseModel):
    """Request to register a webhook for assessment completion callbacks."""

    webhook_url: AnyHttpUrl = Field(
        ...,
        description="URL to call when assessment processing completes",
    )


class WebhookRegisterResponse(BaseModel):
    """Response after registering a webhook."""

    assessment_id: str
    webhook_url: str
    registered_at: str


# Story 3.2: Assessment Result
class RecommendationItemResponse(BaseModel):
    """A single recommended course."""

    rank: int
    course_id: str
    course_title: str
    course_url: str | None = None
    relevance_score: float
    match_reason: str | None = None
    metadata: dict | None = None


class ScoreBreakdownResponse(BaseModel):
    """Score breakdown by category."""

    theoretical: dict | None = None
    profile: dict | None = None
    essay: dict | None = None
    overall: dict | None = None


class AssessmentResultResponse(BaseModel):
    """Full assessment result with recommendations."""

    assessment_id: str
    status: str
    completed: bool
    summary: str | None = None
    overall_score: float | None = None
    score_breakdown: ScoreBreakdownResponse | None = None
    recommendations: list[RecommendationItemResponse] = Field(default_factory=list)
    rag_traces: dict | None = None
    degraded: bool = False
    processing_duration_ms: int | None = None
    completed_at: str | None = None
    message: str | None = None


class AssessmentSummaryEmailResponse(BaseModel):
    """Response after sending assessment summary email."""

    assessment_id: str
    to_email: EmailStr
    resend_id: str
    sent_at: str


# Story 3.3: Feedback
class FeedbackItemRatingPayload(BaseModel):
    """Per-course relevance label used for recommendation quality evaluation."""

    rank: int = Field(..., ge=1, description="Course rank in recommendation list")
    course_id: str = Field(..., min_length=1, description="Recommended course identifier")
    relevance_score_0_2: int = Field(
        ...,
        ge=0,
        le=2,
        description="Per-course relevance score (0=not relevant, 2=highly relevant)",
    )


class FeedbackCreateRequest(BaseModel):
    """Request to submit feedback on recommendations."""

    rating_relevance: int | None = Field(
        None,
        ge=1,
        le=5,
        description="Relevance rating (1-5)",
    )
    rating_acceptance: int | None = Field(
        None,
        ge=1,
        le=5,
        description="Acceptance/usefulness rating (1-5)",
    )
    item_ratings: list[FeedbackItemRatingPayload] | None = Field(
        default=None,
        min_length=1,
        max_length=10,
        description="Optional per-course relevance labels for top recommendations",
    )
    comment: str | None = Field(None, max_length=2000, description="Optional feedback comment")


class FeedbackResponse(BaseModel):
    """Response after submitting feedback."""

    id: str
    recommendation_id: str
    user_id: str
    rating_relevance: int | None = None
    rating_acceptance: int | None = None
    item_ratings: list[FeedbackItemRatingPayload] | None = None
    comment: str | None = None
    created_at: str
