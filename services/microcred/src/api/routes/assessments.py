from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.deps import get_db_session, require_roles
from src.api.schemas.assessments import (
    AssessmentQuestion,
    AssessmentResultResponse,
    AssessmentStartRequest,
    AssessmentStartResponse,
    AssessmentStatusResponse,
    AssessmentSubmitRequest,
    AssessmentSubmitResponse,
    AssessmentSummaryEmailResponse,
    EssayScoreStatus,
    FeedbackCreateRequest,
    FeedbackResponse,
    JobProgress,
    RecommendationItemResponse,
    ScoreBreakdownItem,
    ScoreBreakdownResponse,
    ScoreTypeDetail,
    StageProgress,
    SubmissionScores,
    WebhookRegisterRequest,
    WebhookRegisterResponse,
)
from src.api.schemas.tracks import TrackItem
from src.core.config import get_settings
from src.domain import User
from src.domain.services.assessments import (
    AssessmentService,
    MissingQuestionTemplateError,
    RoleNotFoundError,
)
from src.domain.services.feedback import (
    FeedbackItemRatingsValidationError,
    FeedbackService,
    RecommendationNotFoundError,
)
from src.domain.services.fusion import FusionService
from src.domain.services.status import (
    AssessmentNotFoundError as StatusNotFoundError,
)
from src.domain.services.status import (
    AssessmentNotOwnedError as StatusNotOwnedError,
)
from src.domain.services.status import (
    StatusService,
)
from src.domain.services.submission import (
    AssessmentAlreadySubmittedError,
    AssessmentExpiredError,
    AssessmentNotFoundError,
    AssessmentNotOwnedError,
    DuplicateSubmissionError,
    InvalidResponseError,
    SubmissionService,
)
from src.domain.services.summary_email import (
    AssessmentResultNotReadyError,
    RecipientEmailMissingError,
    SummaryEmailSendError,
    SummaryEmailService,
)
from src.workers.pipeline import process_assessment_jobs

router = APIRouter(prefix="/assessments", tags=["Assessments"])
logger = structlog.get_logger(__name__)


@router.post("/start", response_model=AssessmentStartResponse)
async def start_assessment(
    payload: AssessmentStartRequest,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_roles(["student", "admin"])),
) -> AssessmentStartResponse:
    service = AssessmentService(session)
    try:
        result = await service.start_or_resume(user=user, role_slug=payload.role_slug)
    except RoleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except MissingQuestionTemplateError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return AssessmentStartResponse(
        assessment_id=result["assessment_id"],
        status=result["status"],
        expires_at=result.get("expires_at"),
        role=TrackItem(**result["role"]),
        questions=[AssessmentQuestion(**question) for question in result["questions"]],
    )


@router.delete("/{assessment_id}/abandon")
async def abandon_assessment(
    assessment_id: str,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_roles(["student", "admin"])),
) -> dict[str, str]:
    """
    Abandon/exit a draft or in-progress assessment.

    - Only works for draft or in-progress assessments
    - Deletes the assessment and all associated data
    - Returns success message
    """
    from sqlalchemy import select
    from src.infrastructure.db.models import Assessment, AssessmentStatus

    # Fetch assessment
    stmt = select(Assessment).where(Assessment.id == assessment_id)
    result = await session.execute(stmt)
    assessment = result.scalar_one_or_none()

    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Assessment tidak ditemukan"
        )

    # Check ownership
    if assessment.owner_id != user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Anda tidak memiliki akses ke assessment ini",
        )

    # Can only abandon draft or in-progress
    if assessment.status not in (AssessmentStatus.DRAFT, AssessmentStatus.IN_PROGRESS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Assessment dengan status '{assessment.status.value}' tidak bisa diabandon",
        )

    # Delete assessment (cascade will handle related data)
    await session.delete(assessment)
    await session.commit()

    await logger.ainfo(
        "assessment_abandoned",
        assessment_id=assessment_id,
        user_id=user.user_id,
        role_slug=assessment.role_slug,
    )

    return {"message": "Assessment berhasil dihapus"}


@router.get("/stats/user", response_model=dict[str, Any])
async def get_user_assessment_stats(
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_roles(["student", "admin"])),
) -> dict[str, Any]:
    """
    Get user's assessment statistics.

    Returns:
    - Total completed assessments
    - Completed assessments per role
    - Average score
    """
    from sqlalchemy import func, select
    from src.infrastructure.db.models import Assessment, AssessmentStatus

    # Total completed
    stmt_total = (
        select(func.count(Assessment.id))
        .where(Assessment.owner_id == user.user_id)
        .where(Assessment.status == AssessmentStatus.COMPLETED)
    )
    result = await session.execute(stmt_total)
    total_completed = result.scalar() or 0

    # By role
    stmt_by_role = (
        select(Assessment.role_slug, func.count(Assessment.id))
        .where(Assessment.owner_id == user.user_id)
        .where(Assessment.status == AssessmentStatus.COMPLETED)
        .group_by(Assessment.role_slug)
    )
    result = await session.execute(stmt_by_role)
    by_role = dict(result.all())

    return {
        "total_completed": total_completed,
        "by_role": by_role,
    }


@router.post("/{assessment_id}/submit", response_model=AssessmentSubmitResponse)
async def submit_assessment(
    assessment_id: str,
    background_tasks: BackgroundTasks,
    payload: AssessmentSubmitRequest | None = None,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_roles(["student", "admin"])),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
) -> AssessmentSubmitResponse:
    """
    Submit an assessment for scoring (Story 2.1).

    - Locks all responses
    - Computes rule-based scores for theoretical/profile questions
    - Queues async jobs for GPT essay scoring, RAG, and fusion
    - Supports idempotency key to prevent duplicate submissions
    """
    service = SubmissionService(session)
    responses_payload: list[dict] = []
    if payload and payload.responses:
        responses_payload = [response.model_dump() for response in payload.responses]

    try:
        result = await service.submit_assessment(
            assessment_id=assessment_id,
            user_id=user.user_id,
            idempotency_key=idempotency_key,
            responses_payload=responses_payload,
        )
    except AssessmentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AssessmentNotOwnedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except AssessmentAlreadySubmittedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except AssessmentExpiredError as exc:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail=str(exc)) from exc
    except DuplicateSubmissionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except InvalidResponseError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    settings = get_settings()
    if settings.auto_process_jobs:
        background_tasks.add_task(_run_async_pipeline, result.assessment_id)

    # Convert result to response schema
    return AssessmentSubmitResponse(
        assessment_id=result.assessment_id,
        status=result.status,
        submitted_at=result.submitted_at,
        degraded=result.degraded,
        scores=SubmissionScores(
            theoretical=ScoreTypeDetail(
                total=result.scores["theoretical"]["total"],
                max=result.scores["theoretical"]["max"],
                count=result.scores["theoretical"]["count"],
                percentage=result.scores["theoretical"].get("percentage", 0.0),
                breakdown=[
                    ScoreBreakdownItem(**item)
                    for item in result.scores["theoretical"].get("breakdown", [])
                ],
            ),
            profile=ScoreTypeDetail(
                total=result.scores["profile"]["total"],
                max=result.scores["profile"]["max"],
                count=result.scores["profile"]["count"],
                percentage=result.scores["profile"].get("percentage", 0.0),
                breakdown=[
                    ScoreBreakdownItem(**item)
                    for item in result.scores["profile"].get("breakdown", [])
                ],
            ),
            essay=EssayScoreStatus(
                count=result.scores["essay"]["count"],
                status=result.scores["essay"]["status"],
            ),
        ),
        jobs_queued=result.jobs_queued,
    )


# Story 2.3: Status Polling
@router.get("/{assessment_id}/status", response_model=AssessmentStatusResponse)
async def get_assessment_status(
    assessment_id: str,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_roles(["student", "admin"])),
) -> AssessmentStatusResponse:
    """
    Get current status and progress of an assessment (Story 2.3).

    Returns:
    - Overall progress percentage
    - Stage-by-stage progress (rule_score, gpt, rag, fusion)
    - Individual job statuses
    - Webhook URL if registered
    """
    service = StatusService(session)
    try:
        result = await service.get_assessment_status(
            assessment_id=assessment_id, user_id=user.user_id
        )
    except StatusNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except StatusNotOwnedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    return AssessmentStatusResponse(
        assessment_id=result.assessment_id,
        status=result.status,
        submitted_at=result.submitted_at,
        completed_at=result.completed_at,
        degraded=result.degraded,
        overall_progress=result.overall_progress,
        stages=[
            StageProgress(name=s.name, status=s.status, percentage=s.percentage)
            for s in result.stages
        ],
        jobs=[
            JobProgress(
                job_type=j.job_type,
                status=j.status,
                attempts=j.attempts,
                max_attempts=j.max_attempts,
                started_at=j.started_at,
                completed_at=j.completed_at,
                error=j.error,
                progress_percentage=j.progress_percentage,
                progress_step=j.progress_step,
            )
            for j in result.jobs
        ],
        webhook_url=result.webhook_url,
    )


# Story 2.3: Webhook Registration
@router.post("/{assessment_id}/webhook", response_model=WebhookRegisterResponse)
async def register_webhook(
    assessment_id: str,
    payload: WebhookRegisterRequest,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_roles(["student", "admin"])),
) -> WebhookRegisterResponse:
    """
    Register a webhook URL for assessment completion callbacks (Story 2.3).

    The webhook will be called with a POST request when:
    - All async jobs complete successfully
    - Processing fails after max retries
    """
    service = StatusService(session)
    try:
        result = await service.register_webhook(
            assessment_id=assessment_id,
            user_id=user.user_id,
            webhook_url=str(payload.webhook_url),
        )
    except StatusNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except StatusNotOwnedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    return WebhookRegisterResponse(
        assessment_id=result["assessment_id"],
        webhook_url=result["webhook_url"],
        registered_at=result["registered_at"],
    )


# Story 3.2: Assessment Result
@router.get("/{assessment_id}/result", response_model=AssessmentResultResponse)
async def get_assessment_result(
    assessment_id: str,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_roles(["student", "admin"])),
) -> AssessmentResultResponse:
    """
    Get assessment result with recommendations (Story 3.2).

    Returns:
    - Summary narrative
    - Score breakdown
    - Ranked credential recommendations
    - RAG traces for transparency
    """
    service = FusionService(session)
    try:
        result = await service.get_assessment_result(
            assessment_id=assessment_id,
            user_id=user.user_id,
        )
    except StatusNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except StatusNotOwnedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    # Convert to response model
    return AssessmentResultResponse(
        assessment_id=result["assessment_id"],
        status=result["status"],
        completed=result["completed"],
        summary=result.get("summary"),
        overall_score=result.get("overall_score"),
        score_breakdown=(
            ScoreBreakdownResponse(**result["score_breakdown"])
            if result.get("score_breakdown")
            else None
        ),
        recommendations=[
            RecommendationItemResponse(**rec) for rec in result.get("recommendations", [])
        ],
        rag_traces=result.get("rag_traces"),
        degraded=result.get("degraded", False),
        processing_duration_ms=result.get("processing_duration_ms"),
        completed_at=result.get("completed_at"),
        message=result.get("message"),
    )


@router.post(
    "/{assessment_id}/email-summary",
    response_model=AssessmentSummaryEmailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_summary_email(
    assessment_id: str,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_roles(["student", "admin"])),
) -> AssessmentSummaryEmailResponse:
    """
    Send assessment summary and recommended item links to the user's email.
    """
    service = SummaryEmailService(session)
    try:
        result = await service.send_summary_email(
            assessment_id=assessment_id,
            user_id=user.user_id,
            user_email=user.email,
        )
    except StatusNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except StatusNotOwnedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except AssessmentResultNotReadyError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except RecipientEmailMissingError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except SummaryEmailSendError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return AssessmentSummaryEmailResponse(
        assessment_id=result.assessment_id,
        to_email=result.to_email,
        resend_id=result.resend_id,
        sent_at=result.sent_at,
    )


# Story 3.3: Feedback
@router.post(
    "/{assessment_id}/feedback",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_feedback(
    assessment_id: str,
    payload: FeedbackCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_roles(["student", "advisor", "admin"])),
) -> FeedbackResponse:
    """
    Submit feedback on assessment recommendations (Story 3.3).

    Both students and advisors can submit feedback.
    """
    service = FeedbackService(session)
    try:
        result = await service.create_feedback(
            assessment_id=assessment_id,
            user_id=user.user_id,
            user_role=user.roles[0] if user.roles else "student",
            rating_relevance=payload.rating_relevance,
            rating_acceptance=payload.rating_acceptance,
            item_ratings=[item.model_dump() for item in (payload.item_ratings or [])] or None,
            comment=payload.comment,
        )
    except StatusNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RecommendationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except FeedbackItemRatingsValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return FeedbackResponse(
        id=result["id"],
        recommendation_id=result["recommendation_id"],
        user_id=result["user_id"],
        rating_relevance=result.get("rating_relevance"),
        rating_acceptance=result.get("rating_acceptance"),
        item_ratings=result.get("item_ratings"),
        comment=result.get("comment"),
        created_at=result["created_at"],
    )


async def _run_async_pipeline(assessment_id: str) -> None:
    try:
        await process_assessment_jobs(assessment_id)
    except Exception as exc:  # pragma: no cover - background best effort
        logger.exception(
            "async_pipeline_failed",
            assessment_id=assessment_id,
            error=str(exc),
        )
