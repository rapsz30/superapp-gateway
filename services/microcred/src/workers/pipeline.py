"""High-level helpers for processing assessment jobs sequentially."""

from __future__ import annotations

from dataclasses import dataclass

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.domain.services.fusion import FusionService
from src.domain.services.gpt_scoring import GPTEssayScoringService
from src.domain.services.rag import RAGResult, RAGService
from src.infrastructure.db.models import AsyncJob, JobStatus, JobType
from src.infrastructure.db.session import get_session_factory

logger = structlog.get_logger(__name__)


@dataclass(slots=True)
class JobExecutionResult:
    job_type: str
    status: str
    detail: str | None = None


async def process_assessment_jobs(assessment_id: str) -> list[JobExecutionResult]:
    """Run GPT → RAG → Fusion jobs for an assessment."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        stmt = (
            select(AsyncJob)
            .where(AsyncJob.assessment_id == assessment_id)
            .order_by(AsyncJob.job_type)
        )
        result = await session.execute(stmt)
        jobs = list(result.scalars().all())

        if not jobs:
            logger.warning("pipeline_no_jobs", assessment_id=assessment_id)
            return []

        outcomes: list[JobExecutionResult] = []
        for job_type in (JobType.GPT.value, JobType.RAG.value, JobType.FUSION.value):
            job = next((job for job in jobs if job.job_type == job_type), None)
            if job is None:
                outcomes.append(
                    JobExecutionResult(
                        job_type=job_type,
                        status="missing",
                        detail="Job not created",
                    )
                )
                continue

            if job.status == JobStatus.COMPLETED.value:
                outcomes.append(JobExecutionResult(job_type=job_type, status="completed"))
                continue

            try:
                detail = await _run_single_job(session, assessment_id, job)
                outcomes.append(
                    JobExecutionResult(
                        job_type=job_type,
                        status="completed",
                        detail=detail,
                    )
                )
            except Exception as exc:  # pragma: no cover - logged upstream
                logger.exception(
                    "pipeline_job_failed",
                    assessment_id=assessment_id,
                    job_type=job_type,
                    error=str(exc),
                )
                outcomes.append(
                    JobExecutionResult(
                        job_type=job_type,
                        status="failed",
                        detail=str(exc),
                    )
                )
        return outcomes


async def _run_single_job(session: AsyncSession, assessment_id: str, job: AsyncJob) -> str:
    if job.job_type == JobType.GPT.value:
        service = GPTEssayScoringService(session=session)
        result = await service.score_assessment_essays(assessment_id=assessment_id, job_id=job.id)
        return f"Scored {len(result.essay_scores)} essays"

    if job.job_type == JobType.RAG.value:
        service = RAGService(session=session)
        rag_result: RAGResult = await service.process_rag_job(assessment_id)
        return f"{len(rag_result.matches)} recommendations"

    service = FusionService(session=session)
    fusion_result = await service.process_fusion_job(assessment_id)
    return f"Overall score {fusion_result.overall_score:.1f}"
