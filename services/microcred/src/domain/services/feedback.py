"""
Feedback Service for Story 3.3: Feedback Collection.

Captures advisor/student feedback on recommendations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from sqlalchemy import select
from src.infrastructure.db.models import (
    Assessment,
    Feedback,
    Recommendation,
    RecommendationItem,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


class RecommendationNotFoundError(Exception):
    """Raised when recommendation not found."""


class FeedbackItemRatingsValidationError(Exception):
    """Raised when per-course feedback item ratings payload is invalid."""


class FeedbackService:
    """Service for feedback collection."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_feedback(
        self,
        assessment_id: str,
        user_id: str,
        user_role: str,
        rating_relevance: int | None = None,
        rating_acceptance: int | None = None,
        item_ratings: list[dict[str, object]] | None = None,
        comment: str | None = None,
    ) -> dict:
        """
        Create feedback for an assessment's recommendations.

        AC1: Captures ratings and comments tied to track.
        AC4: Requires proper role and logs events.
        """
        # Get assessment to verify and get track
        stmt = select(Assessment).where(Assessment.id == assessment_id)
        result = await self.session.execute(stmt)
        assessment = result.scalar_one_or_none()

        if not assessment:
            from src.domain.services.status import AssessmentNotFoundError

            raise AssessmentNotFoundError(f"Assessment {assessment_id} not found")

        # Get recommendation
        rec_stmt = select(Recommendation).where(Recommendation.assessment_id == assessment_id)
        rec_result = await self.session.execute(rec_stmt)
        recommendation = rec_result.scalar_one_or_none()

        if not recommendation:
            raise RecommendationNotFoundError(
                f"No recommendation found for assessment {assessment_id}"
            )

        normalized_item_ratings: list[dict[str, object]] | None = None
        if item_ratings:
            items_stmt = select(RecommendationItem).where(
                RecommendationItem.recommendation_id == recommendation.id
            )
            items_result = await self.session.execute(items_stmt)
            recommendation_items = items_result.scalars().all()
            normalized_item_ratings = self._normalize_item_ratings(
                item_ratings=item_ratings,
                recommendation_items=recommendation_items,
            )

        # Create feedback
        feedback = Feedback(
            recommendation_id=recommendation.id,
            user_id=user_id,
            user_role=user_role,
            rating_relevance=rating_relevance,
            rating_acceptance=rating_acceptance,
            item_ratings=normalized_item_ratings,
            comment=comment,
            track_slug=assessment.role_slug,  # AC3: Tagged by track
        )
        self.session.add(feedback)
        await self.session.commit()
        await self.session.refresh(feedback)

        # AC4: Log event
        await logger.ainfo(
            "feedback_submitted",
            feedback_id=feedback.id,
            recommendation_id=recommendation.id,
            user_id=user_id,
            user_role=user_role,
            track_slug=assessment.role_slug,
            rating_relevance=rating_relevance,
            rating_acceptance=rating_acceptance,
            has_item_ratings=bool(normalized_item_ratings),
        )

        return {
            "id": feedback.id,
            "recommendation_id": feedback.recommendation_id,
            "user_id": feedback.user_id,
            "rating_relevance": feedback.rating_relevance,
            "rating_acceptance": feedback.rating_acceptance,
            "item_ratings": feedback.item_ratings,
            "comment": feedback.comment,
            "created_at": feedback.created_at.isoformat(),
        }

    def _normalize_item_ratings(
        self,
        *,
        item_ratings: list[dict[str, object]],
        recommendation_items: list[RecommendationItem],
    ) -> list[dict[str, object]]:
        if not recommendation_items:
            raise FeedbackItemRatingsValidationError(
                "Recommendation items are unavailable for this assessment."
            )

        by_course_id = {item.course_id: item.rank for item in recommendation_items}

        normalized: list[dict[str, object]] = []
        seen_course_ids: set[str] = set()

        for raw in item_ratings:
            if not isinstance(raw, dict):
                raise FeedbackItemRatingsValidationError("Each item rating must be an object.")

            rank_value = raw.get("rank")
            course_id_value = raw.get("course_id")
            score_value = raw.get("relevance_score_0_2")

            if not isinstance(rank_value, int) or rank_value <= 0:
                raise FeedbackItemRatingsValidationError(
                    "Item rating rank must be a positive integer."
                )
            if not isinstance(course_id_value, str) or not course_id_value.strip():
                raise FeedbackItemRatingsValidationError(
                    "Item rating course_id must be a non-empty string."
                )
            if not isinstance(score_value, int) or score_value not in (0, 1, 2):
                raise FeedbackItemRatingsValidationError(
                    "Item rating relevance_score_0_2 must be 0, 1, or 2."
                )

            course_id = course_id_value.strip()
            # Client-provided rank can become stale when recommendations are regenerated.
            # Canonical rank is always derived from recommendation_items in DB.
            score = score_value

            if course_id in seen_course_ids:
                raise FeedbackItemRatingsValidationError(
                    "Duplicate course_id found in item_ratings."
                )

            expected_rank = by_course_id.get(course_id)
            if expected_rank is None:
                raise FeedbackItemRatingsValidationError(
                    f"Course '{course_id}' is not part of this recommendation."
                )

            seen_course_ids.add(course_id)
            normalized.append({
                "rank": expected_rank,
                "course_id": course_id,
                "relevance_score_0_2": score,
            })

        normalized.sort(key=lambda item: int(item["rank"]))
        return normalized

    async def get_feedback_stats(self, track_slug: str | None = None) -> dict:
        """
        Get aggregated feedback statistics.

        AC2: Aggregated feedback metrics.
        AC3: Can filter by track.
        """
        from sqlalchemy import func

        # Build base query
        query = select(
            func.count(Feedback.id).label("total_count"),
            func.avg(Feedback.rating_relevance).label("avg_relevance"),
            func.avg(Feedback.rating_acceptance).label("avg_acceptance"),
        )

        if track_slug:
            query = query.where(Feedback.track_slug == track_slug)

        result = await self.session.execute(query)
        row = result.first()

        return {
            "track_slug": track_slug,
            "total_feedback_count": row.total_count if row else 0,
            "average_relevance_rating": round(row.avg_relevance or 0, 2),
            "average_acceptance_rating": round(row.avg_acceptance or 0, 2),
        }
