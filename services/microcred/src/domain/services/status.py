"""
Status service for assessment progress tracking.

Story 2.3: Status Polling, Webhooks, and Idempotency
- GET /assessments/{id}/status returns stage progress and job status
- Webhook registration for completion callbacks
- Idempotency key enforcement
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from src.infrastructure.db.models import (
    Assessment,
    AssessmentStatus,
    AsyncJob,
)

logger = structlog.get_logger()


class AssessmentNotFoundError(Exception):
    """Raised when assessment does not exist."""


class AssessmentNotOwnedError(Exception):
    """Raised when user does not own the assessment."""


@dataclass(slots=True)
class JobProgressInfo:
    """Progress information for a single job."""

    job_type: str
    status: str
    attempts: int
    max_attempts: int
    started_at: str | None
    completed_at: str | None
    error: str | None
    progress_percentage: float | None
    progress_step: str | None


@dataclass(slots=True)
class StageProgressInfo:
    """Progress information for a processing stage."""

    name: str
    status: str
    percentage: float


@dataclass(slots=True)
class AssessmentStatusResult:
    """Result of status query."""

    assessment_id: str
    status: str
    submitted_at: str | None
    completed_at: str | None
    degraded: bool
    overall_progress: float
    stages: list[StageProgressInfo]
    jobs: list[JobProgressInfo]
    webhook_url: str | None


class StatusService:
    """Service for assessment status and progress tracking."""

    # Stage weights for overall progress calculation
    STAGE_WEIGHTS = {
        "rule_score": 0.25,  # 25% - synchronous, always complete after submit
        "gpt": 0.35,  # 35% - GPT essay scoring
        "rag": 0.25,  # 25% - RAG recommendations
        "fusion": 0.15,  # 15% - Final fusion
    }

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_assessment_status(
        self, *, assessment_id: str, user_id: str
    ) -> AssessmentStatusResult:
        """
        Get current status and progress of an assessment.

        Returns stage-by-stage progress and overall completion percentage.
        """
        # Load assessment with jobs
        stmt = (
            select(Assessment)
            .where(Assessment.id == assessment_id)
            .options(selectinload(Assessment.jobs))
        )
        result = await self.session.execute(stmt)
        assessment = result.scalar_one_or_none()

        if assessment is None:
            raise AssessmentNotFoundError(f"Assessment {assessment_id} not found")

        if assessment.owner_id != user_id:
            raise AssessmentNotOwnedError("You do not own this assessment")

        # Build job progress info
        jobs_info = self._build_jobs_info(assessment.jobs)

        # Build stage progress info
        stages_info = self._build_stages_info(assessment, jobs_info)

        # Calculate overall progress
        overall_progress = self._calculate_overall_progress(assessment, stages_info)

        # Determine completed_at from jobs
        completed_at = self._get_completion_time(assessment, jobs_info)

        return AssessmentStatusResult(
            assessment_id=assessment.id,
            status=assessment.status.value
            if hasattr(assessment.status, "value")
            else str(assessment.status),
            submitted_at=assessment.completed_at.isoformat() if assessment.completed_at else None,
            completed_at=completed_at,
            degraded=assessment.degraded or False,
            overall_progress=overall_progress,
            stages=stages_info,
            jobs=jobs_info,
            webhook_url=getattr(assessment, "webhook_url", None),
        )

    def _build_jobs_info(self, jobs: list[AsyncJob]) -> list[JobProgressInfo]:
        """Build job progress information list."""
        infos: list[JobProgressInfo] = []
        for job in jobs:
            progress_percentage, progress_step = self._extract_job_progress(job.payload)
            infos.append(
                JobProgressInfo(
                    job_type=job.job_type,
                    status=job.status,
                    attempts=job.attempts,
                    max_attempts=job.max_attempts,
                    started_at=job.started_at.isoformat() if job.started_at else None,
                    completed_at=job.completed_at.isoformat() if job.completed_at else None,
                    error=(job.error_payload.get("message") if job.error_payload else None),
                    progress_percentage=progress_percentage,
                    progress_step=progress_step,
                )
            )
        return infos

    def _build_stages_info(
        self, assessment: Assessment, jobs_info: list[JobProgressInfo]
    ) -> list[StageProgressInfo]:
        """Build stage progress information."""
        stages = []

        # Rule score stage - complete if assessment is submitted
        is_submitted = assessment.status in [
            AssessmentStatus.SUBMITTED,
            AssessmentStatus.COMPLETED,
            AssessmentStatus.FAILED,
        ] or str(assessment.status) in ["submitted", "completed", "failed"]

        rule_score_status = "completed" if is_submitted else "pending"
        stages.append(
            StageProgressInfo(
                name="rule_score",
                status=rule_score_status,
                percentage=100.0 if is_submitted else 0.0,
            )
        )

        # Build stage info from jobs
        for stage_name in ["gpt", "rag", "fusion"]:
            job = next((j for j in jobs_info if j.job_type == stage_name), None)

            if job is None:
                # No job yet - depends on submission
                status = "pending" if not is_submitted else "queued"
                percentage = 0.0
            elif job.status == "completed":
                status = "completed"
                percentage = 100.0
            elif job.status == "in_progress":
                status = "in_progress"
                if isinstance(job.progress_percentage, int | float):
                    percentage = max(5.0, min(float(job.progress_percentage), 99.0))
                else:
                    # Legacy fallback when no explicit progress payload is provided.
                    percentage = min(50.0 + (job.attempts * 15.0), 90.0)
            elif job.status == "failed":
                status = "failed"
                percentage = (
                    max(0.0, min(float(job.progress_percentage), 100.0))
                    if isinstance(job.progress_percentage, int | float)
                    else 0.0
                )
            else:  # queued
                status = "queued"
                percentage = (
                    max(0.0, min(float(job.progress_percentage), 100.0))
                    if isinstance(job.progress_percentage, int | float)
                    else 0.0
                )

            stages.append(StageProgressInfo(name=stage_name, status=status, percentage=percentage))

        return stages

    def _calculate_overall_progress(
        self, assessment: Assessment, stages: list[StageProgressInfo]
    ) -> float:
        """Calculate weighted overall progress percentage."""
        status_value = (
            assessment.status.value
            if hasattr(assessment.status, "value")
            else str(assessment.status)
        )
        if status_value == AssessmentStatus.COMPLETED.value:
            return 100.0
        if status_value == AssessmentStatus.FAILED.value and all(
            stage.status in {"completed", "failed"} for stage in stages
        ):
            return 100.0

        total = 0.0
        for stage in stages:
            weight = self.STAGE_WEIGHTS.get(stage.name, 0.0)
            total += stage.percentage * weight
        return round(total, 1)

    def _get_completion_time(
        self, assessment: Assessment, jobs: list[JobProgressInfo]
    ) -> str | None:
        """Get completion time if all jobs are done."""
        if not jobs:
            return None

        # All jobs must be completed or failed
        all_done = all(j.status in ["completed", "failed"] for j in jobs)
        if not all_done:
            return None

        # Find latest completion time
        completion_times = [j.completed_at for j in jobs if j.completed_at]
        if completion_times:
            return max(completion_times)
        return None

    @staticmethod
    def _extract_job_progress(payload: dict | None) -> tuple[float | None, str | None]:
        """Extract job progress percentage and step from payload."""
        if not isinstance(payload, dict):
            return None, None

        progress_data = payload.get("progress")
        percentage: float | None = None
        step: str | None = None

        if isinstance(progress_data, dict):
            raw_percentage = progress_data.get("percentage")
            raw_step = progress_data.get("step")
            if isinstance(raw_percentage, int | float):
                percentage = max(0.0, min(float(raw_percentage), 100.0))
            if isinstance(raw_step, str) and raw_step.strip():
                step = raw_step.strip()
        elif isinstance(progress_data, int | float):
            percentage = max(0.0, min(float(progress_data), 100.0))

        # Backward-compatible fallback keys
        if percentage is None and isinstance(payload.get("progress_percentage"), int | float):
            percentage = max(0.0, min(float(payload["progress_percentage"]), 100.0))
        if step is None and isinstance(payload.get("progress_step"), str):
            stripped = payload["progress_step"].strip()
            step = stripped or None

        return percentage, step

    async def register_webhook(self, *, assessment_id: str, user_id: str, webhook_url: str) -> dict:
        """
        Register a webhook URL for assessment completion callbacks.

        Returns registration confirmation.
        """
        # Load assessment
        stmt = select(Assessment).where(Assessment.id == assessment_id)
        result = await self.session.execute(stmt)
        assessment = result.scalar_one_or_none()

        if assessment is None:
            raise AssessmentNotFoundError(f"Assessment {assessment_id} not found")

        if assessment.owner_id != user_id:
            raise AssessmentNotOwnedError("You do not own this assessment")

        # Update webhook URL
        await self.session.execute(
            update(Assessment).where(Assessment.id == assessment_id).values(webhook_url=webhook_url)
        )
        await self.session.commit()

        now = datetime.now(UTC)

        await logger.ainfo(
            "webhook_registered",
            assessment_id=assessment_id,
            webhook_url=webhook_url,
        )

        return {
            "assessment_id": assessment_id,
            "webhook_url": webhook_url,
            "registered_at": now.isoformat(),
        }
