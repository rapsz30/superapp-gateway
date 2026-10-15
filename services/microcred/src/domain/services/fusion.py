"""
Fusion Service for Story 3.2: Fusion Summary and Result Delivery.

Combines rule scores, essay metrics, and RAG results into a narrative summary.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import structlog
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from src.domain.services.summary_formatter import format_assessment_summary
from src.infrastructure.db.models import (
    Assessment,
    AssessmentQuestionSnapshot,
    AssessmentResponse,
    AssessmentStatus,
    AsyncJob,
    JobStatus,
    JobType,
    QuestionType,
    Recommendation,
    RecommendationItem,
    Score,
    UserModel,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


@dataclass
class ScoreBreakdown:
    """Breakdown of scores by type."""

    theoretical_score: float
    theoretical_max: float
    theoretical_pct: float
    profile_score: float
    profile_max: float
    profile_pct: float
    essay_score: float
    essay_max: float
    essay_pct: float
    overall_score: float
    overall_max: float
    overall_pct: float


@dataclass
class FusionResult:
    """Result from fusion processing."""

    assessment_id: str
    summary: str
    overall_score: float
    score_breakdown: dict
    recommendations: list[dict]
    rag_traces: dict | None
    degraded: bool
    processing_duration_ms: int
    completed_at: str


class FusionError(Exception):
    """Raised when fusion processing fails."""


class FusionService:
    """Service for combining scores and generating recommendation summaries."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _update_job_progress(
        self,
        job: AsyncJob,
        *,
        progress_percentage: float,
        progress_step: str | None = None,
        status: str | None = None,
        payload_extra: dict[str, Any] | None = None,
        error_payload: dict[str, Any] | None = None,
    ) -> None:
        """Persist granular fusion job progress for status polling."""
        now = datetime.now(UTC)
        payload = dict(job.payload or {})
        progress_data = payload.get("progress")
        if not isinstance(progress_data, dict):
            progress_data = {}
        progress_data["percentage"] = round(max(0.0, min(progress_percentage, 100.0)), 1)
        if isinstance(progress_step, str) and progress_step.strip():
            progress_data["step"] = progress_step.strip()
        progress_data["updated_at"] = now.isoformat()
        payload["progress"] = progress_data

        if isinstance(payload_extra, dict):
            payload.update(payload_extra)

        job.payload = payload

        if status is not None:
            job.status = status
            if status == JobStatus.IN_PROGRESS.value:
                if not job.started_at:
                    job.started_at = now
                job.attempts += 1
                job.error_payload = None
            elif status in (JobStatus.COMPLETED.value, JobStatus.FAILED.value):
                job.completed_at = now
                if status == JobStatus.COMPLETED.value:
                    job.error_payload = None

        if error_payload is not None:
            job.error_payload = error_payload

        await self.session.commit()

    @staticmethod
    def _parse_non_negative_int(value: Any) -> int | None:
        if value is None or isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value if value >= 0 else None
        if isinstance(value, float):
            return int(value) if value >= 0 else None
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.isdigit():
                parsed = int(stripped)
                return parsed if parsed >= 0 else None
        return None

    @staticmethod
    def _clean_text_list(value: Any) -> list[str]:
        if isinstance(value, list | tuple | set):
            raw_items = value
        elif value is None:
            raw_items = []
        else:
            raw_items = [value]

        cleaned: list[str] = []
        for item in raw_items:
            text = str(item).strip()
            if text:
                cleaned.append(text)
        return cleaned

    @classmethod
    def _extract_project_profile_payload(
        cls,
        response_data: dict[str, Any],
    ) -> tuple[int | None, list[str]]:
        project_count = cls._parse_non_negative_int(response_data.get("project_count"))
        contexts = cls._clean_text_list(response_data.get("selected_options"))

        if not contexts:
            contexts = cls._clean_text_list(response_data.get("project_contexts"))

        value = response_data.get("value")
        if isinstance(value, dict):
            if project_count is None:
                project_count = cls._parse_non_negative_int(value.get("project_count"))
            if not contexts:
                contexts = cls._clean_text_list(
                    value.get("selected_options") or value.get("project_contexts")
                )
        elif isinstance(value, list) and not contexts:
            contexts = cls._clean_text_list(value)
        elif project_count is None and not isinstance(value, list | dict):
            project_count = cls._parse_non_negative_int(value)

        return project_count, contexts

    async def _get_score_breakdown(self, assessment_id: str) -> ScoreBreakdown:
        """Calculate score breakdown from all scores."""
        stmt = select(Score).where(Score.assessment_id == assessment_id)
        result = await self.session.execute(stmt)
        scores = result.scalars().all()

        theoretical_score = 0.0
        theoretical_max = 0.0
        profile_score = 0.0
        profile_max = 0.0
        essay_score = 0.0
        essay_max = 0.0

        for score in scores:
            if score.question_type == QuestionType.THEORETICAL:
                theoretical_score += score.score
                theoretical_max += score.max_score
            elif score.question_type == QuestionType.PROFILE:
                profile_score += score.score
                profile_max += score.max_score
            elif score.question_type == QuestionType.ESSAY:
                essay_score += score.score
                essay_max += score.max_score

        # Calculate percentages
        theoretical_pct = (theoretical_score / theoretical_max * 100) if theoretical_max > 0 else 0
        profile_pct = (profile_score / profile_max * 100) if profile_max > 0 else 0
        essay_pct = (essay_score / essay_max * 100) if essay_max > 0 else 0

        # Overall score (weighted average)
        total_score = theoretical_score + profile_score + essay_score
        total_max = theoretical_max + profile_max + essay_max
        overall_pct = (total_score / total_max * 100) if total_max > 0 else 0

        return ScoreBreakdown(
            theoretical_score=theoretical_score,
            theoretical_max=theoretical_max,
            theoretical_pct=round(theoretical_pct, 1),
            profile_score=profile_score,
            profile_max=profile_max,
            profile_pct=round(profile_pct, 1),
            essay_score=essay_score,
            essay_max=essay_max,
            essay_pct=round(essay_pct, 1),
            overall_score=total_score,
            overall_max=total_max,
            overall_pct=round(overall_pct, 1),
        )

    def _generate_summary(
        self,
        role_title: str,
        breakdown: ScoreBreakdown,
        recommendations: list[RecommendationItem],
        degraded: bool,
        profile_signals: dict | None = None,
        missed_topics: list[str] | None = None,
        user_name: str | None = None,
        rag_traces: dict | None = None,
    ) -> str:
        """Generate narrative summary from scores and recommendations."""
        readiness = None
        if isinstance(rag_traces, dict):
            readiness_candidate = rag_traces.get("readiness")
            if isinstance(readiness_candidate, dict):
                readiness = readiness_candidate

        return format_assessment_summary(
            role_title=role_title,
            overall_pct=breakdown.overall_pct,
            overall_score=breakdown.overall_score,
            overall_max=breakdown.overall_max,
            theoretical_pct=breakdown.theoretical_pct,
            theoretical_score=breakdown.theoretical_score,
            profile_pct=breakdown.profile_pct,
            profile_score=breakdown.profile_score,
            essay_pct=breakdown.essay_pct,
            essay_score=breakdown.essay_score,
            has_essay=breakdown.essay_max > 0,
            recommendations=recommendations,
            degraded=degraded,
            profile_signals=profile_signals,
            missed_topics=missed_topics,
            user_name=user_name,
            readiness=readiness,
        )

    async def _get_user_name(self, owner_id: str) -> str | None:
        """Get user's full name by owner_id."""
        stmt = select(UserModel.full_name).where(UserModel.id == owner_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _extract_profile_signals(self, assessment_id: str) -> dict:
        """Extract profile signals from assessment responses.

        Returns dict with keys:
            - tech-preferences: What user wants to learn (Q8) - can be custom text
            - content-duration: Preferred duration (Q9)
            - payment-preference: Paid/free preference (Q10)
        """
        stmt = (
            select(AssessmentQuestionSnapshot, AssessmentResponse)
            .join(
                AssessmentResponse,
                AssessmentResponse.question_snapshot_id == AssessmentQuestionSnapshot.id,
            )
            .where(
                AssessmentQuestionSnapshot.assessment_id == assessment_id,
                AssessmentQuestionSnapshot.question_type == QuestionType.PROFILE,
            )
        )
        rows = (await self.session.execute(stmt)).all()
        signals: dict[str, str | list[str] | int] = {}
        for snapshot, response in rows:
            response_data = response.response_data or {}
            key = str((snapshot.metadata_ or {}).get("dimension") or str(snapshot.sequence))

            # Q7 stores structured data (project_count + checklist contexts).
            project_count, project_contexts = self._extract_project_profile_payload(response_data)
            if key in {"experience-level", "experience"}:
                if project_count is not None:
                    signals["experience-project-count"] = project_count
                if project_contexts:
                    signals["experience-project-contexts"] = project_contexts

            # Try multiple keys to get the value (different FE implementations)
            value = (
                response_data.get("value")
                or response_data.get("selected_option")
                or response_data.get("answer")
                or response_data.get("answer_text")
                or response_data.get("custom_text")
                or response_data.get("text")
            )
            if value is None:
                continue

            if isinstance(value, list):
                cleaned = [str(item).strip() for item in value if str(item).strip()]
                if not cleaned:
                    continue
                signals[key] = cleaned
            else:
                text_value = str(value).strip()
                if not text_value:
                    continue
                signals[key] = text_value
        return signals

    async def _extract_missed_topics(self, assessment_id: str) -> list[str]:
        """Extract topics from THEORETICAL/ESSAY questions that scored poorly (< 60%).

        Only extracts topics from non-profile questions to avoid showing
        dimension names like 'experience-level' as missed topics.
        """
        # Profile dimensions to exclude from missed topics
        profile_dimensions = {
            "experience-level",
            "tech-preferences",
            "content-duration",
            "payment-preference",
        }

        stmt = (
            select(Score, AssessmentQuestionSnapshot)
            .join(
                AssessmentQuestionSnapshot,
                AssessmentQuestionSnapshot.id == Score.question_snapshot_id,
            )
            .where(Score.assessment_id == assessment_id)
        )
        rows = (await self.session.execute(stmt)).all()
        missed: list[str] = []
        for score, snapshot in rows:
            if score.max_score <= 0:
                continue
            ratio = score.score / score.max_score
            if ratio >= 0.6:
                continue

            # Skip profile questions - they don't have technical topics
            if snapshot.question_type == QuestionType.PROFILE:
                continue

            # Get topic/dimension from metadata (only if not a profile dimension)
            dimension = (snapshot.metadata_ or {}).get("dimension")
            if dimension and dimension not in profile_dimensions:
                missed.append(str(dimension))

            # Extract key topics from prompt for more context
            prompt = snapshot.prompt or ""
            prompt_lower = prompt.lower()
            # Extract key topics from prompt
            topic_keywords = [
                "api",
                "rest",
                "database",
                "sql",
                "cache",
                "security",
                "testing",
                "docker",
                "kubernetes",
                "microservice",
                "async",
                "authentication",
            ]
            for kw in topic_keywords:
                if kw in prompt_lower and kw not in missed:
                    missed.append(kw)
        return missed

    async def process_fusion_job(self, assessment_id: str) -> FusionResult:
        """
        Process fusion job - combine all scores and generate summary.

        AC1: Combines rule scores, essay metrics, and RAG results into narrative summary.
        AC3: Includes timestamp and processing duration.
        """
        start_time = time.time()

        # Get assessment with role
        stmt = (
            select(Assessment)
            .where(Assessment.id == assessment_id)
            .options(selectinload(Assessment.role))
        )
        result = await self.session.execute(stmt)
        assessment = result.scalar_one_or_none()

        if not assessment:
            raise FusionError(f"Assessment {assessment_id} not found")

        # Get fusion job
        job_stmt = (
            select(AsyncJob)
            .where(
                AsyncJob.assessment_id == assessment_id,
                AsyncJob.job_type == JobType.FUSION.value,
            )
            .order_by(AsyncJob.queued_at.desc())
        )
        job_result = await self.session.execute(job_stmt)
        job = job_result.scalars().first()

        if job:
            await self._update_job_progress(
                job,
                status=JobStatus.IN_PROGRESS.value,
                progress_percentage=10.0,
                progress_step="Collecting score components",
            )

        try:
            # Get score breakdown
            breakdown = await self._get_score_breakdown(assessment_id)
            if job:
                await self._update_job_progress(
                    job,
                    progress_percentage=35.0,
                    progress_step="Calculating weighted scores",
                )

            # Get recommendation and items
            rec_stmt = (
                select(Recommendation)
                .where(Recommendation.assessment_id == assessment_id)
                .options(selectinload(Recommendation.items))
            )
            rec_result = await self.session.execute(rec_stmt)
            recommendation = rec_result.scalar_one_or_none()

            items = recommendation.items if recommendation else []
            degraded = bool(
                (recommendation.degraded if recommendation else False) or assessment.degraded
            )
            rag_traces = recommendation.rag_traces if recommendation else None

            # Extract profile signals for personalization
            profile_signals = await self._extract_profile_signals(assessment_id)

            # Extract missed topics (areas where user needs improvement)
            missed_topics = await self._extract_missed_topics(assessment_id)

            # Get user's name for personalized greeting
            user_name = await self._get_user_name(assessment.owner_id)

            if job:
                await self._update_job_progress(
                    job,
                    progress_percentage=65.0,
                    progress_step="Generating personalized summary",
                )

            # Generate summary with personalization and missed topics
            role_title = assessment.role.name if assessment.role else assessment.role_slug
            summary = self._generate_summary(
                role_title,
                breakdown,
                items,
                degraded,
                profile_signals,
                missed_topics,
                user_name,
                rag_traces,
            )

            # Calculate processing duration
            duration_ms = int((time.time() - start_time) * 1000)

            if job:
                await self._update_job_progress(
                    job,
                    progress_percentage=85.0,
                    progress_step="Persisting final recommendation",
                )

            # Update or create recommendation
            if recommendation:
                recommendation.summary = summary
                recommendation.overall_score = breakdown.overall_score
                recommendation.degraded = degraded
                recommendation.score_breakdown = {
                    "theoretical": {
                        "score": breakdown.theoretical_score,
                        "max": breakdown.theoretical_max,
                        "percentage": breakdown.theoretical_pct,
                    },
                    "profile": {
                        "score": breakdown.profile_score,
                        "max": breakdown.profile_max,
                        "percentage": breakdown.profile_pct,
                    },
                    "essay": {
                        "score": breakdown.essay_score,
                        "max": breakdown.essay_max,
                        "percentage": breakdown.essay_pct,
                    },
                    "overall": {
                        "score": breakdown.overall_score,
                        "max": breakdown.overall_max,
                        "percentage": breakdown.overall_pct,
                    },
                }
                recommendation.processing_duration_ms = duration_ms
            else:
                recommendation = Recommendation(
                    assessment_id=assessment_id,
                    summary=summary,
                    overall_score=breakdown.overall_score,
                    degraded=degraded,
                    score_breakdown={
                        "theoretical": {
                            "score": breakdown.theoretical_score,
                            "max": breakdown.theoretical_max,
                            "percentage": breakdown.theoretical_pct,
                        },
                        "profile": {
                            "score": breakdown.profile_score,
                            "max": breakdown.profile_max,
                            "percentage": breakdown.profile_pct,
                        },
                        "essay": {
                            "score": breakdown.essay_score,
                            "max": breakdown.essay_max,
                            "percentage": breakdown.essay_pct,
                        },
                        "overall": {
                            "score": breakdown.overall_score,
                            "max": breakdown.overall_max,
                            "percentage": breakdown.overall_pct,
                        },
                    },
                    processing_duration_ms=duration_ms,
                )
                self.session.add(recommendation)

            # Update assessment status to completed
            completed_at = datetime.now(UTC)
            assessment.status = AssessmentStatus.COMPLETED
            assessment.degraded = degraded
            assessment.completed_at = completed_at

            if job:
                await self._update_job_progress(
                    job,
                    status=JobStatus.COMPLETED.value,
                    progress_percentage=100.0,
                    progress_step="Completed",
                )
            else:
                await self.session.commit()

            await logger.ainfo(
                "fusion_completed",
                assessment_id=assessment_id,
                overall_score=breakdown.overall_score,
                duration_ms=duration_ms,
            )

            return FusionResult(
                assessment_id=assessment_id,
                summary=summary,
                overall_score=breakdown.overall_score,
                score_breakdown=recommendation.score_breakdown,
                recommendations=[
                    {
                        "rank": item.rank,
                        "course_id": item.course_id,
                        "course_title": item.course_title,
                        "course_url": item.course_url,
                        "relevance_score": item.relevance_score,
                        "match_reason": item.match_reason,
                    }
                    for item in items
                ],
                rag_traces=rag_traces,
                degraded=degraded,
                processing_duration_ms=duration_ms,
                completed_at=completed_at.isoformat(),
            )
        except Exception as exc:
            await self.session.rollback()
            if job:
                await self._update_job_progress(
                    job,
                    status=JobStatus.FAILED.value,
                    progress_percentage=95.0,
                    progress_step="Failed",
                    error_payload={"message": str(exc)},
                )
            raise

    async def get_assessment_result(self, assessment_id: str, user_id: str) -> dict:
        """
        Get assessment result for API response.

        AC2: Returns summary, ranked items, RAG traces, and degraded status.
        """
        # Get assessment
        stmt = (
            select(Assessment)
            .where(Assessment.id == assessment_id)
            .options(selectinload(Assessment.role))
        )
        result = await self.session.execute(stmt)
        assessment = result.scalar_one_or_none()

        if not assessment:
            from src.domain.services.status import AssessmentNotFoundError

            raise AssessmentNotFoundError(f"Assessment {assessment_id} not found")

        if assessment.owner_id != user_id:
            from src.domain.services.status import AssessmentNotOwnedError

            raise AssessmentNotOwnedError("You do not own this assessment")

        # Get recommendation with items
        rec_stmt = (
            select(Recommendation)
            .where(Recommendation.assessment_id == assessment_id)
            .options(selectinload(Recommendation.items))
        )
        rec_result = await self.session.execute(rec_stmt)
        recommendation = rec_result.scalar_one_or_none()
        status_value = (
            assessment.status.value
            if hasattr(assessment.status, "value")
            else str(assessment.status)
        )

        if not recommendation:
            return {
                "assessment_id": assessment_id,
                "status": status_value,
                "message": "Results not yet available. Processing may still be in progress.",
                "completed": False,
            }

        completed = status_value == AssessmentStatus.COMPLETED.value
        degraded = bool(assessment.degraded or recommendation.degraded)
        completed_at = (
            assessment.completed_at.isoformat()
            if assessment.completed_at
            else recommendation.created_at.isoformat()
        )

        return {
            "assessment_id": assessment_id,
            "status": status_value,
            "completed": completed,
            "summary": recommendation.summary,
            "overall_score": recommendation.overall_score,
            "score_breakdown": recommendation.score_breakdown,
            "recommendations": [
                {
                    "rank": item.rank,
                    "course_id": item.course_id,
                    "course_title": item.course_title,
                    "course_url": item.course_url,
                    "relevance_score": item.relevance_score,
                    "match_reason": item.match_reason,
                    "metadata": item.course_metadata,
                }
                for item in recommendation.items
            ],
            "rag_traces": recommendation.rag_traces,
            "degraded": degraded,
            "processing_duration_ms": recommendation.processing_duration_ms,
            "completed_at": completed_at,
        }
