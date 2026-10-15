"""
Unit tests for Story 3.3: Feedback Collection.

Tests feedback submission and aggregation.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from src.domain.services.feedback import (
    FeedbackItemRatingsValidationError,
    FeedbackService,
    RecommendationNotFoundError,
)


class TestFeedbackCreation:
    """Tests for feedback submission."""

    @pytest.fixture
    def mock_session(self):
        """Mock database session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def feedback_service(self, mock_session):
        """Create FeedbackService instance."""
        return FeedbackService(mock_session)

    @pytest.mark.asyncio
    async def test_create_feedback_success(self, mock_session, feedback_service):
        """Test successful feedback creation."""
        from src.infrastructure.db.models import Assessment, Feedback, Recommendation

        # Mock assessment
        mock_assessment = MagicMock(spec=Assessment)
        mock_assessment.id = "assessment-123"
        mock_assessment.role_slug = "backend-engineer"

        # Mock recommendation
        mock_recommendation = MagicMock(spec=Recommendation)
        mock_recommendation.id = "rec-123"
        mock_recommendation.assessment_id = "assessment-123"

        # Mock feedback after creation
        mock_feedback = MagicMock(spec=Feedback)
        mock_feedback.id = "feedback-123"
        mock_feedback.recommendation_id = "rec-123"
        mock_feedback.user_id = "user-456"
        mock_feedback.rating_relevance = 4
        mock_feedback.rating_acceptance = 5
        mock_feedback.comment = "Great recommendations!"
        mock_feedback.created_at = MagicMock()
        mock_feedback.created_at.isoformat.return_value = "2024-01-01T00:00:00"

        # Setup mock execute
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.side_effect = [mock_assessment, mock_recommendation]
        mock_session.execute.return_value = mock_result
        mock_session.refresh = AsyncMock()

        # Patch add to capture the feedback object
        created_feedback = None

        def capture_feedback(obj):
            nonlocal created_feedback
            created_feedback = obj
            # Copy attributes from mock
            obj.id = mock_feedback.id
            obj.recommendation_id = mock_feedback.recommendation_id
            obj.user_id = mock_feedback.user_id
            obj.rating_relevance = mock_feedback.rating_relevance
            obj.rating_acceptance = mock_feedback.rating_acceptance
            obj.comment = mock_feedback.comment
            obj.created_at = mock_feedback.created_at

        mock_session.add = capture_feedback

        result = await feedback_service.create_feedback(
            assessment_id="assessment-123",
            user_id="user-456",
            user_role="student",
            rating_relevance=4,
            rating_acceptance=5,
            comment="Great recommendations!",
        )

        assert result["id"] == "feedback-123"
        assert result["rating_relevance"] == 4
        assert result["rating_acceptance"] == 5

    @pytest.mark.asyncio
    async def test_create_feedback_assessment_not_found(self, mock_session, feedback_service):
        """Test feedback creation with non-existent assessment."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        from src.domain.services.status import AssessmentNotFoundError

        with pytest.raises(AssessmentNotFoundError):
            await feedback_service.create_feedback(
                assessment_id="nonexistent",
                user_id="user-123",
                user_role="student",
            )

    @pytest.mark.asyncio
    async def test_create_feedback_recommendation_not_found(self, mock_session, feedback_service):
        """Test feedback creation with no recommendation."""
        from src.infrastructure.db.models import Assessment

        # Assessment exists
        mock_assessment = MagicMock(spec=Assessment)
        mock_assessment.id = "assessment-123"
        mock_assessment.role_slug = "backend-engineer"

        # But no recommendation
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.side_effect = [mock_assessment, None]
        mock_session.execute.return_value = mock_result

        with pytest.raises(RecommendationNotFoundError):
            await feedback_service.create_feedback(
                assessment_id="assessment-123",
                user_id="user-123",
                user_role="advisor",
            )

    @pytest.mark.asyncio
    async def test_create_feedback_with_item_ratings_success(self, mock_session, feedback_service):
        """Test successful feedback creation with per-course item ratings."""
        from src.infrastructure.db.models import (
            Assessment,
            Feedback,
            Recommendation,
            RecommendationItem,
        )

        mock_assessment = MagicMock(spec=Assessment)
        mock_assessment.id = "assessment-123"
        mock_assessment.role_slug = "backend-engineer"

        mock_recommendation = MagicMock(spec=Recommendation)
        mock_recommendation.id = "rec-123"
        mock_recommendation.assessment_id = "assessment-123"

        item1 = MagicMock(spec=RecommendationItem)
        item1.rank = 1
        item1.course_id = "course-1"
        item2 = MagicMock(spec=RecommendationItem)
        item2.rank = 2
        item2.course_id = "course-2"

        assessment_result = MagicMock()
        assessment_result.scalar_one_or_none.return_value = mock_assessment
        recommendation_result = MagicMock()
        recommendation_result.scalar_one_or_none.return_value = mock_recommendation
        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = [item1, item2]
        mock_session.execute = AsyncMock(
            side_effect=[assessment_result, recommendation_result, items_result]
        )
        mock_session.refresh = AsyncMock()

        def capture_feedback(obj: Feedback):
            obj.id = "feedback-123"
            obj.recommendation_id = "rec-123"
            obj.user_id = "user-456"
            obj.rating_relevance = 4
            obj.rating_acceptance = 5
            obj.comment = "Great recommendations!"
            obj.created_at = MagicMock()
            obj.created_at.isoformat.return_value = "2024-01-01T00:00:00"

        mock_session.add = capture_feedback

        result = await feedback_service.create_feedback(
            assessment_id="assessment-123",
            user_id="user-456",
            user_role="student",
            rating_relevance=4,
            rating_acceptance=5,
            item_ratings=[
                {"rank": 2, "course_id": "course-2", "relevance_score_0_2": 1},
                {"rank": 1, "course_id": "course-1", "relevance_score_0_2": 2},
            ],
            comment="Great recommendations!",
        )

        assert result["id"] == "feedback-123"
        assert result["item_ratings"] == [
            {"rank": 1, "course_id": "course-1", "relevance_score_0_2": 2},
            {"rank": 2, "course_id": "course-2", "relevance_score_0_2": 1},
        ]

    @pytest.mark.asyncio
    async def test_create_feedback_with_mismatched_rank_is_normalized(
        self,
        mock_session,
        feedback_service,
    ):
        """Mismatched rank payload should be normalized to canonical DB rank."""
        from src.infrastructure.db.models import (
            Assessment,
            Feedback,
            Recommendation,
            RecommendationItem,
        )

        mock_assessment = MagicMock(spec=Assessment)
        mock_assessment.id = "assessment-123"
        mock_assessment.role_slug = "backend-engineer"

        mock_recommendation = MagicMock(spec=Recommendation)
        mock_recommendation.id = "rec-123"
        mock_recommendation.assessment_id = "assessment-123"

        item1 = MagicMock(spec=RecommendationItem)
        item1.rank = 1
        item1.course_id = "course-1"
        item2 = MagicMock(spec=RecommendationItem)
        item2.rank = 2
        item2.course_id = "course-2"

        assessment_result = MagicMock()
        assessment_result.scalar_one_or_none.return_value = mock_assessment
        recommendation_result = MagicMock()
        recommendation_result.scalar_one_or_none.return_value = mock_recommendation
        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = [item1, item2]
        mock_session.execute = AsyncMock(
            side_effect=[assessment_result, recommendation_result, items_result]
        )
        mock_session.refresh = AsyncMock()

        def capture_feedback(obj: Feedback):
            obj.id = "feedback-123"
            obj.recommendation_id = "rec-123"
            obj.user_id = "user-456"
            obj.rating_relevance = None
            obj.rating_acceptance = None
            obj.comment = None
            obj.created_at = MagicMock()
            obj.created_at.isoformat.return_value = "2024-01-01T00:00:00"

        mock_session.add = capture_feedback

        result = await feedback_service.create_feedback(
            assessment_id="assessment-123",
            user_id="user-456",
            user_role="student",
            item_ratings=[
                {"rank": 99, "course_id": "course-1", "relevance_score_0_2": 2},
                {"rank": 1, "course_id": "course-2", "relevance_score_0_2": 1},
            ],
        )

        assert result["item_ratings"] == [
            {"rank": 1, "course_id": "course-1", "relevance_score_0_2": 2},
            {"rank": 2, "course_id": "course-2", "relevance_score_0_2": 1},
        ]

    @pytest.mark.asyncio
    async def test_create_feedback_with_invalid_item_ratings_raises(
        self,
        mock_session,
        feedback_service,
    ):
        """Unknown course in item ratings should raise validation error."""
        from src.infrastructure.db.models import Assessment, Recommendation, RecommendationItem

        mock_assessment = MagicMock(spec=Assessment)
        mock_assessment.id = "assessment-123"
        mock_assessment.role_slug = "backend-engineer"

        mock_recommendation = MagicMock(spec=Recommendation)
        mock_recommendation.id = "rec-123"
        mock_recommendation.assessment_id = "assessment-123"

        item1 = MagicMock(spec=RecommendationItem)
        item1.rank = 1
        item1.course_id = "course-1"

        assessment_result = MagicMock()
        assessment_result.scalar_one_or_none.return_value = mock_assessment
        recommendation_result = MagicMock()
        recommendation_result.scalar_one_or_none.return_value = mock_recommendation
        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = [item1]
        mock_session.execute = AsyncMock(
            side_effect=[assessment_result, recommendation_result, items_result]
        )

        with pytest.raises(FeedbackItemRatingsValidationError):
            await feedback_service.create_feedback(
                assessment_id="assessment-123",
                user_id="user-456",
                user_role="student",
                item_ratings=[
                    {"rank": 2, "course_id": "course-x", "relevance_score_0_2": 2},
                ],
            )


class TestFeedbackValidation:
    """Tests for feedback validation."""

    @pytest.fixture
    def mock_session(self):
        """Mock database session."""
        return AsyncMock()

    @pytest.fixture
    def feedback_service(self, mock_session):
        """Create FeedbackService instance."""
        return FeedbackService(mock_session)

    @pytest.mark.asyncio
    async def test_rating_values_accepted(self, mock_session, feedback_service):
        """Test valid rating values (1-5) are accepted."""
        from src.infrastructure.db.models import Assessment, Recommendation

        mock_assessment = MagicMock(spec=Assessment)
        mock_assessment.id = "assessment-123"
        mock_assessment.role_slug = "backend-engineer"

        mock_recommendation = MagicMock(spec=Recommendation)
        mock_recommendation.id = "rec-123"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.side_effect = [mock_assessment, mock_recommendation]
        mock_session.execute.return_value = mock_result
        mock_session.refresh = AsyncMock()

        def mock_add(obj):
            obj.id = "new-feedback"
            obj.recommendation_id = "rec-123"
            obj.user_id = "user-1"
            obj.rating_relevance = 5
            obj.rating_acceptance = 1
            obj.comment = None
            obj.created_at = MagicMock()
            obj.created_at.isoformat.return_value = "2024-01-01T00:00:00"

        mock_session.add = mock_add

        # Should not raise for valid ratings
        result = await feedback_service.create_feedback(
            assessment_id="assessment-123",
            user_id="user-1",
            user_role="student",
            rating_relevance=5,
            rating_acceptance=1,
        )

        assert result["rating_relevance"] == 5
        assert result["rating_acceptance"] == 1

    @pytest.mark.asyncio
    async def test_optional_fields_nullable(self, mock_session, feedback_service):
        """Test feedback with only required fields."""
        from src.infrastructure.db.models import Assessment, Recommendation

        mock_assessment = MagicMock(spec=Assessment)
        mock_assessment.id = "assessment-123"
        mock_assessment.role_slug = "backend-engineer"

        mock_recommendation = MagicMock(spec=Recommendation)
        mock_recommendation.id = "rec-123"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.side_effect = [mock_assessment, mock_recommendation]
        mock_session.execute.return_value = mock_result
        mock_session.refresh = AsyncMock()

        def mock_add(obj):
            obj.id = "new-feedback"
            obj.recommendation_id = "rec-123"
            obj.user_id = "user-1"
            obj.rating_relevance = None
            obj.rating_acceptance = None
            obj.comment = None
            obj.created_at = MagicMock()
            obj.created_at.isoformat.return_value = "2024-01-01T00:00:00"

        mock_session.add = mock_add

        # Should work with no ratings or comment
        result = await feedback_service.create_feedback(
            assessment_id="assessment-123",
            user_id="user-1",
            user_role="advisor",
        )

        assert result["rating_relevance"] is None
        assert result["rating_acceptance"] is None
        assert result["comment"] is None


class TestFeedbackStats:
    """Tests for feedback aggregation."""

    @pytest.fixture
    def mock_session(self):
        """Mock database session."""
        return AsyncMock()

    @pytest.fixture
    def feedback_service(self, mock_session):
        """Create FeedbackService instance."""
        return FeedbackService(mock_session)

    @pytest.mark.asyncio
    async def test_get_stats_all_tracks(self, mock_session, feedback_service):
        """Test getting aggregate stats for all tracks."""
        mock_row = MagicMock()
        mock_row.total_count = 100
        mock_row.avg_relevance = 4.2
        mock_row.avg_acceptance = 3.8

        mock_result = MagicMock()
        mock_result.first.return_value = mock_row
        mock_session.execute.return_value = mock_result

        stats = await feedback_service.get_feedback_stats()

        assert stats["total_feedback_count"] == 100
        assert stats["average_relevance_rating"] == 4.2
        assert stats["average_acceptance_rating"] == 3.8
        assert stats["track_slug"] is None

    @pytest.mark.asyncio
    async def test_get_stats_by_track(self, mock_session, feedback_service):
        """Test getting stats filtered by track."""
        mock_row = MagicMock()
        mock_row.total_count = 25
        mock_row.avg_relevance = 4.5
        mock_row.avg_acceptance = 4.0

        mock_result = MagicMock()
        mock_result.first.return_value = mock_row
        mock_session.execute.return_value = mock_result

        stats = await feedback_service.get_feedback_stats(track_slug="backend-engineer")

        assert stats["track_slug"] == "backend-engineer"
        assert stats["total_feedback_count"] == 25

    @pytest.mark.asyncio
    async def test_get_stats_no_feedback(self, mock_session, feedback_service):
        """Test stats when no feedback exists."""
        mock_row = MagicMock()
        mock_row.total_count = 0
        mock_row.avg_relevance = None
        mock_row.avg_acceptance = None

        mock_result = MagicMock()
        mock_result.first.return_value = mock_row
        mock_session.execute.return_value = mock_result

        stats = await feedback_service.get_feedback_stats()

        assert stats["total_feedback_count"] == 0
        assert stats["average_relevance_rating"] == 0
        assert stats["average_acceptance_rating"] == 0
