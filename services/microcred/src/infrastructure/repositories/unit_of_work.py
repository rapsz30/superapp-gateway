from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import structlog

logger = structlog.get_logger()


@dataclass
class AssessmentRepository:
    """Placeholder repository for assessment entities."""

    async def mark_scoring_started(self, assessment_id: str) -> None:
        logger.info("assessment_mark_scoring_started", assessment_id=assessment_id)

    async def store_score(self, assessment_id: str, score: float) -> None:
        logger.info(
            "assessment_store_score",
            assessment_id=assessment_id,
            score=score,
        )


@dataclass
class RecommendationRepository:
    """Placeholder repository for recommendation entities."""

    async def save_recommendations(
        self,
        user_id: str,
        recommendations: list[dict[str, Any]],
    ) -> None:
        logger.info(
            "recommendations_save",
            user_id=user_id,
            recommendations=recommendations,
        )


class UnitOfWork:
    """Repository/unit-of-work abstraction placeholder."""

    def __init__(self) -> None:
        self.assessments = AssessmentRepository()
        self.recommendations = RecommendationRepository()

    async def __aenter__(self) -> UnitOfWork:
        logger.debug("uow_enter")
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if exc:
            await self.rollback()
        else:
            await self.commit()
        logger.debug("uow_exit", exc_type=str(exc_type) if exc_type else None)

    async def commit(self) -> None:
        logger.debug("uow_commit")

    async def rollback(self) -> None:
        logger.debug("uow_rollback")
