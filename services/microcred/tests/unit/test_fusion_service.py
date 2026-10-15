"""
Unit tests for Story 3.2: Fusion Summary & Results Endpoint.

Tests the fusion service and result retrieval.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from src.domain.services.fusion import FusionService, ScoreBreakdown
from src.infrastructure.db.models import AssessmentStatus


class TestFusionServiceSummary:
    """Tests for FusionService summary generation."""

    @pytest.fixture
    def mock_session(self):
        """Mock database session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def fusion_service(self, mock_session):
        """Create FusionService instance."""
        return FusionService(mock_session)

    def test_generate_summary_high_score(self, fusion_service):
        """Test summary for high scoring assessment."""
        breakdown = ScoreBreakdown(
            theoretical_score=85.0,
            theoretical_max=100.0,
            theoretical_pct=85.0,
            profile_score=80.0,
            profile_max=100.0,
            profile_pct=80.0,
            essay_score=90.0,
            essay_max=100.0,
            essay_pct=90.0,
            overall_score=255.0,
            overall_max=300.0,
            overall_pct=85.0,
        )

        summary = fusion_service._generate_summary(
            role_title="Backend Engineer",
            breakdown=breakdown,
            recommendations=[],
            degraded=False,
        )

        # Should be encouraging for high scores
        assert "excellent" in summary.lower()
        assert "85.0 pts" in summary

    def test_generate_summary_low_score(self, fusion_service):
        """Test summary for low scoring assessment."""
        breakdown = ScoreBreakdown(
            theoretical_score=45.0,
            theoretical_max=100.0,
            theoretical_pct=45.0,
            profile_score=50.0,
            profile_max=100.0,
            profile_pct=50.0,
            essay_score=40.0,
            essay_max=100.0,
            essay_pct=40.0,
            overall_score=135.0,
            overall_max=300.0,
            overall_pct=45.0,
        )

        summary = fusion_service._generate_summary(
            role_title="Frontend Engineer",
            breakdown=breakdown,
            recommendations=[],
            degraded=False,
        )

        # Should mention areas for development (in English)
        # "Thank you" = for low score message, "strengthen" = needs to strengthen foundation
        assert "thank you" in summary.lower() or "strengthen" in summary.lower()

    def test_generate_summary_medium_score(self, fusion_service):
        """Test summary for medium scoring assessment."""
        breakdown = ScoreBreakdown(
            theoretical_score=65.0,
            theoretical_max=100.0,
            theoretical_pct=65.0,
            profile_score=70.0,
            profile_max=100.0,
            profile_pct=70.0,
            essay_score=65.0,
            essay_max=100.0,
            essay_pct=65.0,
            overall_score=200.0,
            overall_max=300.0,
            overall_pct=66.7,
        )

        summary = fusion_service._generate_summary(
            role_title="Data Scientist",
            breakdown=breakdown,
            recommendations=[],
            degraded=False,
        )

        # Should be balanced - "good" message (now in Indonesian: "Good job!")
        assert "good" in summary.lower()

    def test_generate_summary_includes_breakdown(self, fusion_service):
        """Test summary includes score breakdown section."""
        breakdown = ScoreBreakdown(
            theoretical_score=75.0,
            theoretical_max=100.0,
            theoretical_pct=75.0,
            profile_score=80.0,
            profile_max=100.0,
            profile_pct=80.0,
            essay_score=70.0,
            essay_max=100.0,
            essay_pct=70.0,
            overall_score=225.0,
            overall_max=300.0,
            overall_pct=75.0,
        )

        summary = fusion_service._generate_summary(
            role_title="DevOps Engineer",
            breakdown=breakdown,
            recommendations=[],
            degraded=False,
        )

        assert "Score Breakdown" in summary
        assert "Theory" in summary

    def test_generate_summary_with_degraded_notice(self, fusion_service):
        """Test summary includes degraded mode notice."""
        breakdown = ScoreBreakdown(
            theoretical_score=75.0,
            theoretical_max=100.0,
            theoretical_pct=75.0,
            profile_score=80.0,
            profile_max=100.0,
            profile_pct=80.0,
            essay_score=0.0,
            essay_max=0.0,
            essay_pct=0.0,
            overall_score=155.0,
            overall_max=200.0,
            overall_pct=77.5,
        )

        summary = fusion_service._generate_summary(
            role_title="Backend Engineer",
            breakdown=breakdown,
            recommendations=[],
            degraded=True,
        )

        assert "limited" in summary.lower() or "constraints" in summary.lower()

    def test_generate_summary_two_path_prioritizes_mandatory_when_below_threshold(
        self, fusion_service
    ):
        """Summary should show top-5 sections per path and threshold-based priority guidance."""

        class FakeRecommendationItem:
            def __init__(
                self,
                title: str,
                path: str,
                score: float,
            ) -> None:
                self.course_title = title
                self.course_id = title.lower().replace(" ", "-")
                self.course_url = None
                self.relevance_score = score
                self.match_reason = "Recommended for your current readiness."
                self.course_metadata = {
                    "learning_path": path,
                    "learning_path_label": (
                        "Mandatory Foundation" if path == "mandatory_foundation" else "Target Path"
                    ),
                    "level": "Beginner Level" if path == "mandatory_foundation" else "Expert Level",
                    "is_paid": "False",
                }

        breakdown = ScoreBreakdown(
            theoretical_score=55.0,
            theoretical_max=100.0,
            theoretical_pct=55.0,
            profile_score=60.0,
            profile_max=100.0,
            profile_pct=60.0,
            essay_score=0.0,
            essay_max=0.0,
            essay_pct=0.0,
            overall_score=115.0,
            overall_max=200.0,
            overall_pct=57.5,
        )

        recommendations = [
            FakeRecommendationItem("API Fundamentals", "mandatory_foundation", 0.85),
            FakeRecommendationItem("SQL Foundations", "mandatory_foundation", 0.82),
            FakeRecommendationItem("AWS Advanced Patterns", "target_path", 0.79),
            FakeRecommendationItem("GraphQL at Scale", "target_path", 0.75),
        ]

        summary = fusion_service._generate_summary(
            role_title="Backend Engineer",
            breakdown=breakdown,
            recommendations=recommendations,
            degraded=False,
            profile_signals={"tech-preferences": "aws, graphql"},
            rag_traces={
                "readiness": {
                    "force_foundation": True,
                    "advanced_kkm": 70.0,
                    "overall_pct": 57.5,
                    "learning_paths": {"mode": "two-path"},
                    "reason": "Your score is below advanced threshold, start from fundamentals.",
                }
            },
        )

        assert "Mandatory Foundation (Top 5)" in summary
        assert "Target Path (Top 5)" in summary
        assert "Minimum readiness threshold: **140.0 / 200.0 pts**" in summary
        assert "Prioritize **Mandatory Foundation** first" in summary

    def test_generate_summary_includes_q7_project_experience_and_score_usage_note(
        self, fusion_service
    ):
        """Summary should include Q7 project details and recommendation scoring inputs."""

        class FakeRecommendationItem:
            def __init__(self) -> None:
                self.course_title = "Backend Foundations"
                self.course_id = "backend-foundations"
                self.course_url = None
                self.relevance_score = 0.61
                self.match_reason = "Mandatory Foundation • Beginner level • 8.0h duration"
                self.course_metadata = {
                    "learning_path": "mandatory_foundation",
                    "level": "Beginner Level",
                    "is_paid": "False",
                }

        breakdown = ScoreBreakdown(
            theoretical_score=180.0,
            theoretical_max=300.0,
            theoretical_pct=60.0,
            profile_score=150.0,
            profile_max=400.0,
            profile_pct=37.5,
            essay_score=20.0,
            essay_max=300.0,
            essay_pct=6.7,
            overall_score=350.0,
            overall_max=1000.0,
            overall_pct=35.0,
        )

        summary = fusion_service._generate_summary(
            role_title="Backend Engineer",
            breakdown=breakdown,
            recommendations=[FakeRecommendationItem()],
            degraded=False,
            profile_signals={
                "tech-preferences": "azure, graphql",
                "content-duration": "short",
                "payment-preference": "free",
                "experience-project-count": 4,
                "experience-project-contexts": ["personal", "production"],
            },
            rag_traces={
                "readiness": {
                    "force_foundation": True,
                    "advanced_threshold_pct": 70.0,
                    "overall_pct": 35.0,
                    "overall_score": 350.0,
                    "overall_max": 1000.0,
                    "learning_paths": {"mode": "two-path"},
                    "reason": "Focus on mandatory foundation first.",
                }
            },
        )

        assert "From your **Q7 project experience**, you reported **4 projects**" in summary
        assert "personal projects" in summary
        assert "production projects" in summary
        assert (
            "Recommendations are ranked using your **theoretical**, **essay**, and **profile**"
            in summary
        )
        assert "filtered by your **payment** and **content duration** preferences." in summary


class TestFusionServiceScoreBreakdown:
    """Tests for score breakdown calculation."""

    @pytest.fixture
    def mock_session(self):
        """Mock database session."""
        session = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_get_score_breakdown_returns_dataclass(self, mock_session):
        """Test score breakdown returns ScoreBreakdown dataclass."""
        from src.infrastructure.db.models import QuestionType, Score

        # Mock scores
        mock_score1 = MagicMock(spec=Score)
        mock_score1.question_type = QuestionType.THEORETICAL
        mock_score1.score = 80.0
        mock_score1.max_score = 100.0

        mock_score2 = MagicMock(spec=Score)
        mock_score2.question_type = QuestionType.PROFILE
        mock_score2.score = 70.0
        mock_score2.max_score = 100.0

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_score1, mock_score2]
        mock_session.execute.return_value = mock_result

        service = FusionService(mock_session)
        breakdown = await service._get_score_breakdown("test-assessment")

        assert isinstance(breakdown, ScoreBreakdown)
        assert breakdown.theoretical_score == 80.0
        assert breakdown.profile_score == 70.0

    @pytest.mark.asyncio
    async def test_score_breakdown_calculates_percentages(self, mock_session):
        """Test score breakdown calculates correct percentages."""
        from src.infrastructure.db.models import QuestionType, Score

        mock_score = MagicMock(spec=Score)
        mock_score.question_type = QuestionType.THEORETICAL
        mock_score.score = 50.0
        mock_score.max_score = 100.0

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_score]
        mock_session.execute.return_value = mock_result

        service = FusionService(mock_session)
        breakdown = await service._get_score_breakdown("test-assessment")

        assert breakdown.theoretical_pct == 50.0

    @pytest.mark.asyncio
    async def test_score_breakdown_handles_zero_max(self, mock_session):
        """Test score breakdown handles zero max score."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        service = FusionService(mock_session)
        breakdown = await service._get_score_breakdown("test-assessment")

        # Should not divide by zero
        assert breakdown.theoretical_pct == 0
        assert breakdown.overall_pct == 0


class TestFusionProfileSignals:
    """Tests for profile signal extraction."""

    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_extract_profile_signals_includes_q7_project_fields(self, mock_session):
        """Q7 structured payload should be exposed for summary/recommendation usage."""
        snapshot_q7 = MagicMock()
        snapshot_q7.metadata_ = {"dimension": "experience-level"}
        response_q7 = MagicMock()
        response_q7.response_data = {
            "project_count": 5,
            "selected_options": ["personal", "production"],
        }

        snapshot_q8 = MagicMock()
        snapshot_q8.metadata_ = {"dimension": "tech-preferences"}
        response_q8 = MagicMock()
        response_q8.response_data = {"value": "azure, graphql"}

        mock_result = MagicMock()
        mock_result.all.return_value = [
            (snapshot_q7, response_q7),
            (snapshot_q8, response_q8),
        ]
        mock_session.execute.return_value = mock_result

        service = FusionService(mock_session)
        signals = await service._extract_profile_signals("assessment-id")

        assert signals["experience-project-count"] == 5
        assert signals["experience-project-contexts"] == ["personal", "production"]
        assert signals["tech-preferences"] == "azure, graphql"


class TestFusionServiceGetResult:
    """Tests for result retrieval."""

    @pytest.fixture
    def mock_session(self):
        """Mock database session."""
        session = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_get_result_not_found(self, mock_session):
        """Test get result for non-existent assessment."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        service = FusionService(mock_session)

        from src.domain.services.status import AssessmentNotFoundError

        with pytest.raises(AssessmentNotFoundError):
            await service.get_assessment_result("nonexistent-id", "user-123")

    @pytest.mark.asyncio
    async def test_get_result_not_owned(self, mock_session):
        """Test get result for assessment owned by another user."""
        from src.infrastructure.db.models import Assessment

        mock_assessment = MagicMock(spec=Assessment)
        mock_assessment.id = "test-123"
        mock_assessment.owner_id = "other-user"
        mock_assessment.status = "completed"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_assessment
        mock_session.execute.return_value = mock_result

        service = FusionService(mock_session)

        from src.domain.services.status import AssessmentNotOwnedError

        with pytest.raises(AssessmentNotOwnedError):
            await service.get_assessment_result("test-123", "user-123")

    @pytest.mark.asyncio
    async def test_get_result_merges_degraded_and_uses_assessment_completed_at(self, mock_session):
        """Result should use assessment degraded/completed_at as source of truth."""
        assessment_result = MagicMock()
        assessment = MagicMock()
        assessment.id = "test-123"
        assessment.owner_id = "user-123"
        assessment.status = AssessmentStatus.COMPLETED
        assessment.degraded = True
        assessment.completed_at = datetime(2026, 2, 11, 18, 30, 35, tzinfo=UTC)
        assessment_result.scalar_one_or_none.return_value = assessment

        recommendation_result = MagicMock()
        recommendation = MagicMock()
        recommendation.summary = "Summary"
        recommendation.overall_score = 700.0
        recommendation.score_breakdown = {"overall": {"score": 700.0, "percentage": 100.0}}
        recommendation.items = []
        recommendation.rag_traces = {"match_count": 5}
        recommendation.degraded = False
        recommendation.processing_duration_ms = 115
        recommendation.created_at = datetime(2026, 2, 11, 18, 30, 17, tzinfo=UTC)
        recommendation_result.scalar_one_or_none.return_value = recommendation

        mock_session.execute.side_effect = [assessment_result, recommendation_result]

        service = FusionService(mock_session)
        result = await service.get_assessment_result("test-123", "user-123")

        assert result["status"] == "completed"
        assert result["completed"] is True
        assert result["degraded"] is True
        assert result["completed_at"] == "2026-02-11T18:30:35+00:00"
