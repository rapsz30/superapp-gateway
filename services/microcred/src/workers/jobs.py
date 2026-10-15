"""
Worker Jobs for Async Processing.

Story 2.2: GPT Essay Scoring Worker
Story 2.3: RAG Recommendations Worker (placeholder)
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

import structlog
from src.domain.services.gpt_scoring import (
    EssayScoringResult,
    GPTEssayScoringService,
)
from src.infrastructure.db.session import async_session_factory
from src.libs.gpt_client import GPTClientProtocol

if TYPE_CHECKING:
    pass

logger = structlog.get_logger()


def score_essay_job(
    assessment_id: str,
    job_id: str,
    gpt_client: GPTClientProtocol | None = None,
) -> dict[str, Any]:
    """
    Entry point for running essay scoring asynchronously.

    AC1: Worker pulls essay responses from Redis queue.
    AC2: Calls GPT with deterministic prompt and rubric.
    AC3: Retries handled by GPT client with exponential backoff.
    AC4: On failure, logs diagnostics and marks job as failed.

    Args:
        assessment_id: The assessment to score essays for.
        job_id: The async job ID for status tracking.
        gpt_client: Optional GPT client (for testing injection).

    Returns:
        Dictionary with scoring results.
    """
    return asyncio.run(_score_essay_async(assessment_id, job_id, gpt_client))


def generate_recommendations_job(
    user_id: str,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Entry point for generating recommendations."""
    return asyncio.run(_generate_recommendations_async(user_id, context or {}))


async def _score_essay_async(
    assessment_id: str,
    job_id: str,
    gpt_client: GPTClientProtocol | None = None,
) -> dict[str, Any]:
    """
    Score all essay responses for an assessment.

    Story 2.2 AC:
    - Worker pulls essay responses per assessment
    - Batches and sends to GPT with deterministic prompt
    - Parses responses into rubric metrics
    - Stores scores in database
    - Updates job status throughout
    """
    async with async_session_factory() as session:
        service = GPTEssayScoringService(
            session=session,
            gpt_client=gpt_client,
        )

        try:
            result: EssayScoringResult = await service.score_assessment_essays(
                assessment_id=assessment_id,
                job_id=job_id,
            )

            logger.info(
                "essay_scoring_completed",
                assessment_id=assessment_id,
                job_id=job_id,
                status=result.status,
                scored_count=len(result.essay_scores),
                failed_count=result.failed_count,
                parse_error_count=result.parse_error_count,
                parse_recovery_count=result.parse_recovery_count,
                retry_used_count=result.retry_used_count,
                total_score=result.total_score,
                max_score=result.max_score,
            )

            return {
                "assessment_id": assessment_id,
                "job_id": job_id,
                "status": result.status,
                "scored_count": len(result.essay_scores),
                "failed_count": result.failed_count,
                "fallback_count": result.fallback_count,
                "hard_failed_count": result.hard_failed_count,
                "parse_error_count": result.parse_error_count,
                "parse_recovery_count": result.parse_recovery_count,
                "retry_used_count": result.retry_used_count,
                "total_score": result.total_score,
                "max_score": result.max_score,
            }

        except Exception as e:
            logger.error(
                "essay_scoring_job_failed",
                assessment_id=assessment_id,
                job_id=job_id,
                error=str(e),
                exc_info=True,
            )
            return {
                "assessment_id": assessment_id,
                "job_id": job_id,
                "status": "failed",
                "error": str(e),
            }


async def _generate_recommendations_async(user_id: str, context: dict[str, Any]) -> dict[str, Any]:
    """Placeholder for RAG recommendations - Story 2.3."""
    recommendations = context.get("recommendations", [])
    # TODO: Implement with actual RAG service in Story 2.3
    result = {
        "user_id": user_id,
        "status": "queued",
        "recommendations": recommendations,
    }
    logger.info("recommendations_enqueued", **result)
    return result
