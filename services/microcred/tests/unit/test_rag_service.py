"""
Unit tests for Story 3.1: RAG Retrieval Service.

Tests the keyword-based course recommendation system.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from src.domain.services.rag import CourseMatch, RAGResult, RAGService
from src.infrastructure.repositories.course_enrichment import EnrichedCourseMetadata


class TestRAGService:
    """Tests for RAGService."""

    @pytest.fixture
    def mock_session(self):
        """Mock database session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def rag_service(self, mock_session):
        """Create RAGService instance."""
        return RAGService(mock_session)

    def test_build_query_for_backend_engineer(self, rag_service):
        """Test query building for backend-engineer role."""
        query = rag_service._build_query("backend-engineer")

        # Should contain backend role keywords
        assert any(kw in query.lower() for kw in ["python", "api", "java", "node", "database"])

    def test_build_query_for_frontend_engineer(self, rag_service):
        """Test query building for frontend-engineer role."""
        query = rag_service._build_query("frontend-engineer")

        # Should contain frontend role keywords
        assert any(kw in query.lower() for kw in ["javascript", "react", "vue", "angular", "css"])

    def test_build_query_for_data_scientist(self, rag_service):
        """Test query building for data-scientist role."""
        query = rag_service._build_query("data-scientist")

        assert "data" in query.lower() or "python" in query.lower()

    def test_build_query_for_unknown_role(self, rag_service):
        """Test query building for unknown role returns empty or generic."""
        query = rag_service._build_query("unknown-role")

        # Unknown role may return empty or use profile signals
        assert isinstance(query, str)

    def test_build_query_with_profile_signals(self, rag_service):
        """Test query includes profile signals."""
        profile_signals = {"skill1": "database optimization", "skill2": "python"}
        query = rag_service._build_query("backend-engineer", profile_signals=profile_signals)

        # Query should incorporate profile signals
        assert "database" in query.lower() or "python" in query.lower()

    def test_build_query_with_essay_keywords(self, rag_service):
        """Test query includes essay keywords."""
        essay_keywords = ["microservices", "kubernetes"]
        query = rag_service._build_query("backend-engineer", essay_keywords=essay_keywords)

        # Should include essay keywords
        assert "microservices" in query.lower() or "kubernetes" in query.lower()

    def test_calculate_relevance_with_matches(self, rag_service):
        """Test relevance calculation with keyword matches."""
        course = {
            "course_title": "Python Backend Development Masterclass",
            "subject": "Web Development",
        }
        query_terms = ["python", "backend", "development"]

        score = rag_service._calculate_relevance(course, query_terms)

        assert score > 0  # Should have some relevance

    def test_calculate_relevance_no_match(self, rag_service):
        """Test relevance calculation with no keyword match."""
        course = {
            "course_title": "Cooking Basics",
            "subject": "Lifestyle",
        }
        query_terms = ["python", "backend", "api"]

        score = rag_service._calculate_relevance(course, query_terms)

        assert score == 0  # No matches

    def test_readiness_policy_forces_foundation_when_not_meeting_kkm(self, rag_service):
        """Advanced target should be gated to foundational courses when score is low."""
        policy = rag_service._build_readiness_policy(
            role_slug="backend-engineer",
            profile_signals={"tech-preferences": "aws, graphql"},
            score_metrics={
                "overall_pct": 52.0,
                "theoretical_pct": 58.0,
                "profile_pct": 38.0,
                "essay_pct": 0.0,
                "has_essay_scores": False,
            },
        )

        assert policy["targeting_advanced"] is True
        assert policy["advanced_eligible"] is False
        assert policy["force_foundation"] is True
        assert policy["difficulty_pref"] == "beginner"

    def test_readiness_policy_allows_advanced_when_score_is_strong(self, rag_service):
        """Advanced track is allowed when score passes KKM."""
        policy = rag_service._build_readiness_policy(
            role_slug="backend-engineer",
            profile_signals={"tech-preferences": "aws, graphql"},
            score_metrics={
                "overall_pct": 82.0,
                "theoretical_pct": 80.0,
                "profile_pct": 72.0,
                "essay_pct": 76.0,
                "has_essay_scores": True,
            },
        )

        assert policy["targeting_advanced"] is True
        assert policy["advanced_eligible"] is True
        assert policy["force_foundation"] is False

    def test_readiness_policy_forces_foundation_for_low_score_even_non_advanced_target(
        self, rag_service
    ):
        """Low readiness with explicit target should return two-path mode."""
        policy = rag_service._build_readiness_policy(
            role_slug="backend-engineer",
            profile_signals={"tech-preferences": "python"},
            score_metrics={
                "overall_pct": 48.0,
                "theoretical_pct": 50.0,
                "profile_pct": 35.0,
                "essay_pct": 0.0,
                "has_essay_scores": False,
            },
        )

        assert policy["has_target_preferences"] is True
        assert policy["advanced_eligible"] is False
        assert policy["force_foundation"] is True
        assert policy["foundation_priority"] is True

    def test_readiness_policy_sets_foundation_priority_without_target_preferences(
        self, rag_service
    ):
        """Low readiness without target preference should still prioritize foundation path."""
        policy = rag_service._build_readiness_policy(
            role_slug="backend-engineer",
            profile_signals={},
            score_metrics={
                "overall_pct": 20.0,
                "theoretical_pct": 30.0,
                "profile_pct": 25.0,
                "essay_pct": 10.0,
                "has_essay_scores": True,
            },
        )

        assert policy["has_target_preferences"] is False
        assert policy["force_foundation"] is False
        assert policy["foundation_priority"] is True

    def test_readiness_policy_increases_threshold_for_advanced_targets(self, rag_service):
        """Advanced tech targets should increase final readiness threshold above base."""
        policy = rag_service._build_readiness_policy(
            role_slug="backend-engineer",
            profile_signals={"tech-preferences": "aws, kubernetes"},
            score_metrics={
                "overall_pct": 82.0,
                "theoretical_pct": 80.0,
                "profile_pct": 72.0,
                "essay_pct": 76.0,
                "has_essay_scores": True,
            },
            advanced_threshold_pct=70.0,
        )

        assert policy["base_advanced_threshold_pct"] == 70.0
        assert policy["advanced_threshold_pct"] > 70.0
        assert policy["target_complexity"] == "advanced"
        assert policy["threshold_adjustments"]["complexity"] > 0

    def test_readiness_policy_recalibrated_threshold_stays_realistic_for_strong_profile(
        self, rag_service
    ):
        """Recalibrated hybrid should stay above base for advanced targets but not over-inflate."""
        policy = rag_service._build_readiness_policy(
            role_slug="backend-engineer",
            profile_signals={"tech-preferences": "aws, kubernetes"},
            score_metrics={
                "overall_pct": 78.0,
                "theoretical_pct": 88.0,
                "profile_pct": 55.0,
                "essay_pct": 0.0,
                "has_essay_scores": False,
            },
            advanced_threshold_pct=70.0,
        )

        assert policy["base_advanced_threshold_pct"] == 70.0
        assert policy["advanced_threshold_pct"] > 70.0
        assert policy["advanced_threshold_pct"] <= 75.0
        assert policy["threshold_adjustments"]["prerequisite_gap"] == 0.0

    def test_readiness_policy_reduces_threshold_for_foundation_targets_with_experience(
        self, rag_service
    ):
        """Foundation targets and solid project evidence should lower threshold."""
        policy = rag_service._build_readiness_policy(
            role_slug="backend-engineer",
            profile_signals={
                "tech-preferences": "python, sql",
                "experience-project-count": 6,
                "experience-project-contexts": ["production", "team project"],
            },
            score_metrics={
                "overall_pct": 74.0,
                "theoretical_pct": 78.0,
                "profile_pct": 80.0,
                "essay_pct": 70.0,
                "has_essay_scores": True,
            },
            advanced_threshold_pct=70.0,
        )

        assert policy["admin_base_advanced_threshold_pct"] == 70.0
        assert policy["base_advanced_threshold_pct"] < 70.0
        assert policy["advanced_threshold_pct"] < 70.0
        assert policy["threshold_adjustments"]["experience_bonus"] > 0

    def test_difficulty_gate_filters_out_advanced_courses(self, rag_service):
        """Beginner difficulty gate should exclude intermediate/advanced courses."""
        beginner_course = {
            "course_id": "c1",
            "course_title": "AWS Basics for Beginners",
            "subject": "Web Development",
            "url": "http://test.com/c1",
            "level": "Beginner Level",
            "content_duration": 4.0,
            "is_paid": "False",
            "price": 0.0,
            "num_subscribers": 1000,
            "num_reviews": 100,
            "_vector": rag_service._hash_embedding(["aws", "basics"]),
            "_enriched": EnrichedCourseMetadata(
                course_id="c1",
                title="AWS Basics for Beginners",
                tech_tags=["aws"],
                difficulty="beginner",
                is_free=True,
                payment_type="free",
                price=0.0,
                duration_hours=4.0,
                duration_category="short",
                num_subscribers=1000,
                num_reviews=100,
                num_lectures=20,
                quality_score=0.6,
                popularity_score=0.2,
                engagement_score=0.4,
                level="Beginner Level",
                subject="Web Development",
                url="http://test.com/c1",
                published_timestamp="2025-01-01T00:00:00Z",
            ),
        }
        advanced_course = {
            "course_id": "c2",
            "course_title": "AWS Advanced Architecture",
            "subject": "Web Development",
            "url": "http://test.com/c2",
            "level": "Expert Level",
            "content_duration": 15.0,
            "is_paid": "True",
            "price": 49.0,
            "num_subscribers": 2000,
            "num_reviews": 150,
            "_vector": rag_service._hash_embedding(["aws", "advanced"]),
            "_enriched": EnrichedCourseMetadata(
                course_id="c2",
                title="AWS Advanced Architecture",
                tech_tags=["aws"],
                difficulty="advanced",
                is_free=False,
                payment_type="paid",
                price=49.0,
                duration_hours=15.0,
                duration_category="medium",
                num_subscribers=2000,
                num_reviews=150,
                num_lectures=50,
                quality_score=0.7,
                popularity_score=0.3,
                engagement_score=0.4,
                level="Expert Level",
                subject="Web Development",
                url="http://test.com/c2",
                published_timestamp="2025-01-01T00:00:00Z",
            ),
        }

        matches = rag_service._score_and_filter_courses(
            courses=[beginner_course, advanced_course],
            role_slug="backend-engineer",
            query_terms=["aws"],
            query_vec=rag_service._hash_embedding(["aws"]),
            missed_topics=[],
            tech_pref_keywords=["aws"],
            payment_pref="any",
            duration_pref="any",
            top_k=5,
            difficulty_pref="beginner",
            strict_payment=True,
        )

        assert len(matches) == 1
        assert matches[0].course_id == "c1"

    def test_role_fallback_keywords_exclude_advanced_bias(self, rag_service):
        """Role fallback keywords should not be dominated by advanced targets."""
        fallback = rag_service._get_role_fallback_keywords("backend-engineer")

        lowered = [item.lower() for item in fallback]
        assert "api" in lowered
        assert "database" in lowered
        assert "sql" in lowered
        assert "aws" not in lowered

    def test_min_keyword_guard_filters_irrelevant_foundation_fill(self, rag_service):
        """Low-signal irrelevant courses should be filtered during broad foundation fallback."""
        relevant_course = {
            "course_id": "backend-1",
            "course_title": "REST API with Python Flask",
            "subject": "Web Development",
            "url": "http://test.com/backend-1",
            "level": "Beginner Level",
            "content_duration": 5.0,
            "is_paid": "False",
            "price": 0.0,
            "num_subscribers": 500,
            "num_reviews": 50,
            "_vector": rag_service._hash_embedding(["rest", "api", "python"]),
            "_enriched": EnrichedCourseMetadata(
                course_id="backend-1",
                title="REST API with Python Flask",
                tech_tags=["python", "api"],
                difficulty="beginner",
                is_free=True,
                payment_type="free",
                price=0.0,
                duration_hours=5.0,
                duration_category="medium",
                num_subscribers=500,
                num_reviews=50,
                num_lectures=20,
                quality_score=0.4,
                popularity_score=0.1,
                engagement_score=0.3,
                level="Beginner Level",
                subject="Web Development",
                url="http://test.com/backend-1",
                published_timestamp="2025-01-01T00:00:00Z",
            ),
        }
        irrelevant_course = {
            "course_id": "music-1",
            "course_title": "Piano for Beginners",
            "subject": "Musical Instruments",
            "url": "http://test.com/music-1",
            "level": "Beginner Level",
            "content_duration": 30.0,
            "is_paid": "True",
            "price": 19.0,
            "num_subscribers": 70000,
            "num_reviews": 2000,
            "_vector": rag_service._hash_embedding(["piano", "music"]),
            "_enriched": EnrichedCourseMetadata(
                course_id="music-1",
                title="Piano for Beginners",
                tech_tags=["music", "instruments"],
                difficulty="beginner",
                is_free=False,
                payment_type="paid",
                price=19.0,
                duration_hours=30.0,
                duration_category="long",
                num_subscribers=70000,
                num_reviews=2000,
                num_lectures=120,
                quality_score=0.9,
                popularity_score=0.8,
                engagement_score=0.7,
                level="Beginner Level",
                subject="Musical Instruments",
                url="http://test.com/music-1",
                published_timestamp="2025-01-01T00:00:00Z",
            ),
        }

        matches = rag_service._score_and_filter_courses(
            courses=[relevant_course, irrelevant_course],
            role_slug="backend-engineer",
            query_terms=["python", "api", "backend"],
            query_vec=rag_service._hash_embedding(["python", "api", "backend"]),
            missed_topics=[],
            tech_pref_keywords=[],
            payment_pref="any",
            duration_pref="any",
            top_k=5,
            difficulty_pref="beginner",
            min_keyword_score=0.05,
            strict_payment=False,
        )

        assert len(matches) == 1
        assert matches[0].course_id == "backend-1"

    def test_tag_matches_with_learning_path_sets_metadata(self, rag_service):
        """Learning path tags should be embedded in metadata and reason."""
        source = [
            CourseMatch(
                course_id="course-1",
                title="API Fundamentals",
                url="http://example.com/course-1",
                relevance_score=0.77,
                match_reason="Matches your interest in: api",
                metadata={"level": "Beginner Level"},
            )
        ]

        tagged = rag_service._tag_matches_with_learning_path(
            source,
            path_key="mandatory_foundation",
            path_label="Mandatory Foundation",
        )

        assert len(tagged) == 1
        assert tagged[0].metadata["learning_path"] == "mandatory_foundation"
        assert tagged[0].metadata["learning_path_label"] == "Mandatory Foundation"
        assert tagged[0].match_reason.startswith("Mandatory Foundation")

    def test_merge_unique_matches_prioritizes_primary_then_secondary(self, rag_service):
        """Primary list order should win, with secondary filling remaining slots uniquely."""
        primary = [
            CourseMatch("c1", "Course 1", None, 0.9, "r1", {}),
            CourseMatch("c2", "Course 2", None, 0.8, "r2", {}),
        ]
        secondary = [
            CourseMatch("c2", "Course 2 Duplicate", None, 0.7, "r2b", {}),
            CourseMatch("c3", "Course 3", None, 0.6, "r3", {}),
        ]

        merged = rag_service._merge_unique_matches(primary, secondary, limit=3)

        assert [m.course_id for m in merged] == ["c1", "c2", "c3"]

    def test_target_coverage_context_reports_catalog_and_topk_gaps(self, rag_service):
        """Coverage trace should capture catalog availability and top-k misses."""
        mock_courses = [
            {
                "course_title": "AWS for Backend Engineers",
                "subject": "Web Development",
                "level": "Intermediate Level",
                "_enriched": EnrichedCourseMetadata(
                    course_id="c1",
                    title="AWS for Backend Engineers",
                    tech_tags=["aws", "cloud"],
                    difficulty="intermediate",
                    is_free=False,
                    payment_type="paid",
                    price=30.0,
                    duration_hours=5.0,
                    duration_category="medium",
                    num_subscribers=5000,
                    num_reviews=200,
                    num_lectures=40,
                    quality_score=0.7,
                    popularity_score=0.4,
                    engagement_score=0.5,
                    level="Intermediate Level",
                    subject="Web Development",
                    url="http://example.com/c1",
                    published_timestamp="2025-01-01T00:00:00Z",
                ),
            },
            {
                "course_title": "Redis Essentials",
                "subject": "Web Development",
                "level": "Beginner Level",
                "_enriched": EnrichedCourseMetadata(
                    course_id="c2",
                    title="Redis Essentials",
                    tech_tags=["redis"],
                    difficulty="beginner",
                    is_free=True,
                    payment_type="free",
                    price=0.0,
                    duration_hours=3.0,
                    duration_category="short",
                    num_subscribers=2000,
                    num_reviews=120,
                    num_lectures=20,
                    quality_score=0.6,
                    popularity_score=0.3,
                    engagement_score=0.4,
                    level="Beginner Level",
                    subject="Web Development",
                    url="http://example.com/c2",
                    published_timestamp="2025-01-01T00:00:00Z",
                ),
            },
        ]

        with patch.object(rag_service, "_load_courses", return_value=mock_courses):
            coverage = rag_service._compute_target_coverage_context(
                target_keywords=["aws", "graphql", "redis"],
                target_matches=[
                    CourseMatch(
                        course_id="c2",
                        title="Redis Essentials",
                        url="http://example.com/c2",
                        relevance_score=0.6,
                        match_reason="Target Path • Matches your interest in: redis",
                        metadata={"tech_tags": ["redis"]},
                    ),
                ],
            )

        assert coverage["target_keywords"] == ["aws", "graphql", "redis"]
        assert coverage["covered_keywords"] == ["redis"]
        assert coverage["catalog_missing_keywords"] == ["graphql"]
        assert "aws" in coverage["missing_keywords"]
        assert coverage["covered_count"] == 1
        assert coverage["target_count"] == 3
        assert coverage["coverage_percentage"] == 33.0
        assert coverage["coverage_ratio"] == pytest.approx(0.33, abs=0.01)
        assert isinstance(coverage["note"], str) and coverage["note"]

    @pytest.mark.asyncio
    async def test_extract_profile_signals_captures_q7_project_payload(self, rag_service):
        """RAG profile extraction should include structured Q7 inputs."""
        snapshot_q7 = MagicMock()
        snapshot_q7.metadata_ = {"dimension": "experience-level"}
        snapshot_q7.sequence = 7
        response_q7 = MagicMock()
        response_q7.response_data = {
            "project_count": 3,
            "project_contexts": ["kampus", "production"],
        }

        snapshot_q9 = MagicMock()
        snapshot_q9.metadata_ = {"dimension": "content-duration"}
        snapshot_q9.sequence = 9
        response_q9 = MagicMock()
        response_q9.response_data = {"value": "short"}

        mock_result = MagicMock()
        mock_result.all.return_value = [
            (snapshot_q7, response_q7),
            (snapshot_q9, response_q9),
        ]
        rag_service.session.execute.return_value = mock_result

        signals = await rag_service._extract_profile_signals("assessment-id")
        assert signals["experience-project-count"] == 3
        assert signals["experience-project-contexts"] == ["kampus", "production"]
        assert signals["content-duration"] == "short"

    @pytest.mark.asyncio
    async def test_two_path_mode_returns_top_five_per_path(self, rag_service):
        """Two-path mode should keep top-5 mandatory and top-5 target recommendations."""
        foundation_matches = [
            CourseMatch(
                course_id=f"foundation-{idx}",
                title=f"Foundation Course {idx}",
                url=f"http://example.com/foundation-{idx}",
                relevance_score=0.9 - (idx * 0.01),
                match_reason="Strong foundation fit",
                metadata={},
            )
            for idx in range(1, 6)
        ]
        target_matches = [
            CourseMatch(
                course_id=f"target-{idx}",
                title=f"GraphQL Target Course {idx}",
                url=f"http://example.com/target-{idx}",
                relevance_score=0.8 - (idx * 0.01),
                match_reason="Advanced target fit for graphql",
                metadata={"tech_tags": ["api", "graphql"]},
            )
            for idx in range(1, 6)
        ]

        retrieve_mock = AsyncMock(
            side_effect=[
                RAGResult(
                    query="foundation query",
                    matches=foundation_matches,
                    degraded=False,
                    error=None,
                    readiness={"force_foundation": True},
                ),
                RAGResult(
                    query="target query",
                    matches=target_matches,
                    degraded=False,
                    error=None,
                    readiness={"force_foundation": False},
                ),
            ]
        )

        with patch.object(rag_service, "retrieve_recommendations", retrieve_mock):
            result = await rag_service._retrieve_with_learning_paths(
                assessment_id="assessment-1",
                role_slug="backend-engineer",
                profile_signals={"tech-preferences": "aws, graphql"},
                essay_keywords=["api"],
                missed_topics=["database"],
                readiness_policy={
                    "force_foundation": True,
                    "overall_pct": 55.0,
                    "advanced_kkm": 70.0,
                },
            )

        assert len(result.matches) == 10

        mandatory_matches = [
            m
            for m in result.matches
            if str((m.metadata or {}).get("learning_path")) == "mandatory_foundation"
        ]
        target_path_matches = [
            m
            for m in result.matches
            if str((m.metadata or {}).get("learning_path")) == "target_path"
        ]
        assert len(mandatory_matches) == 5
        assert len(target_path_matches) == 5
        assert result.readiness["learning_paths"]["mandatory_foundation_count"] == 5
        assert result.readiness["learning_paths"]["target_path_count"] == 5
        mandatory_ids = {m.course_id for m in mandatory_matches}
        target_ids = {m.course_id for m in target_path_matches}
        assert mandatory_ids.isdisjoint(target_ids)

        assert retrieve_mock.await_count == 2
        first_call = retrieve_mock.await_args_list[0].kwargs
        second_call = retrieve_mock.await_args_list[1].kwargs
        assert first_call["top_k"] == 5
        assert second_call["top_k"] == 5
        assert "tech-preferences" not in dict(first_call["profile_signals"])
        assert second_call["enable_fallback"] is False

    @pytest.mark.asyncio
    async def test_two_path_target_uses_relaxed_fallback_when_empty(self, rag_service):
        """If target path is empty, relax filters and retry without generic fallback."""
        foundation_matches = [
            CourseMatch(
                course_id=f"foundation-{idx}",
                title=f"Foundation Course {idx}",
                url=f"http://example.com/foundation-{idx}",
                relevance_score=0.9 - (idx * 0.01),
                match_reason="Strong foundation fit",
                metadata={},
            )
            for idx in range(1, 6)
        ]
        fallback_target_matches = [
            CourseMatch(
                course_id="target-1",
                title="GraphQL Backend Patterns",
                url="http://example.com/target-1",
                relevance_score=0.69,
                match_reason="Fallback target fit for graphql",
                metadata={"tech_tags": ["api", "graphql"]},
            ),
            CourseMatch(
                course_id="target-2",
                title="CI/CD Pipeline Essentials",
                url="http://example.com/target-2",
                relevance_score=0.68,
                match_reason="Fallback target fit for ci/cd",
                metadata={"tech_tags": ["cicd"]},
            ),
        ]

        retrieve_mock = AsyncMock(
            side_effect=[
                RAGResult(
                    query="foundation query",
                    matches=foundation_matches,
                    degraded=False,
                    error=None,
                    readiness={"force_foundation": True},
                ),
                RAGResult(
                    query="target strict query",
                    matches=[],
                    degraded=False,
                    error=None,
                    readiness={"force_foundation": False},
                ),
                RAGResult(
                    query="target relaxed query",
                    matches=fallback_target_matches,
                    degraded=False,
                    error=None,
                    readiness={"force_foundation": False},
                ),
            ]
        )

        with patch.object(rag_service, "retrieve_recommendations", retrieve_mock):
            result = await rag_service._retrieve_with_learning_paths(
                assessment_id="assessment-1",
                role_slug="backend-engineer",
                profile_signals={
                    "tech-preferences": "graphql, ci/cd",
                    "content-duration": "short",
                    "payment-preference": "free",
                },
                essay_keywords=["api"],
                missed_topics=["database"],
                readiness_policy={
                    "force_foundation": True,
                    "overall_pct": 37.0,
                    "advanced_kkm": 70.0,
                },
            )

        assert retrieve_mock.await_count == 3
        second_call = retrieve_mock.await_args_list[1].kwargs
        third_call = retrieve_mock.await_args_list[2].kwargs
        assert second_call["enable_fallback"] is False
        assert third_call["enable_fallback"] is False
        assert third_call["profile_signals"]["content-duration"] == "any"
        assert third_call["profile_signals"]["payment-preference"] == "any"

        assert result.readiness["learning_paths"]["target_path_fallback_used"] is True
        assert result.readiness["learning_paths"]["target_path_count"] == 2
        assert (
            "broadened by relaxing duration/payment filters"
            in result.readiness["learning_paths"]["note"]
        )

    @pytest.mark.asyncio
    async def test_foundation_priority_without_target_returns_mandatory_only(self, rag_service):
        """Low readiness without target preferences should return mandatory-focused output."""
        foundation_matches = [
            CourseMatch(
                course_id=f"foundation-{idx}",
                title=f"Foundation Course {idx}",
                url=f"http://example.com/foundation-{idx}",
                relevance_score=0.8 - (idx * 0.01),
                match_reason="Foundation fit",
                metadata={},
            )
            for idx in range(1, 6)
        ]

        retrieve_mock = AsyncMock(
            return_value=RAGResult(
                query="foundation query",
                matches=foundation_matches,
                degraded=False,
                error=None,
                readiness={"foundation_priority": True},
            )
        )

        with patch.object(rag_service, "retrieve_recommendations", retrieve_mock):
            result = await rag_service._retrieve_with_learning_paths(
                assessment_id="assessment-1",
                role_slug="backend-engineer",
                profile_signals={},
                essay_keywords=["api"],
                missed_topics=["database"],
                readiness_policy={
                    "force_foundation": False,
                    "foundation_priority": True,
                    "has_target_preferences": False,
                },
            )

        assert retrieve_mock.await_count == 1
        assert len(result.matches) == 5
        assert result.readiness["learning_paths"]["mode"] == "two-path"
        assert result.readiness["learning_paths"]["mandatory_foundation_count"] == 5
        assert result.readiness["learning_paths"]["target_path_count"] == 0
        assert all(
            (match.metadata or {}).get("learning_path") == "mandatory_foundation"
            for match in result.matches
        )


class TestRAGServiceRetrieval:
    """Integration-style tests for RAG retrieval."""

    @pytest.fixture
    def mock_session(self):
        """Mock database session."""
        session = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_retrieve_recommendations_returns_rag_result(self, mock_session):
        """Test retrieve returns a RAGResult with matches."""
        from src.domain.services.rag import RAGResult

        service = RAGService(mock_session)

        # Mock loading courses
        with patch.object(
            service,
            "_load_courses",
            return_value=[
                {
                    "course_id": "1",
                    "course_title": "Python Basics",
                    "subject": "Programming",
                    "url": "http://test.com/1",
                },
                {
                    "course_id": "2",
                    "course_title": "Java Advanced",
                    "subject": "Programming",
                    "url": "http://test.com/2",
                },
            ],
        ):
            result = await service.retrieve_recommendations(
                assessment_id="test-123",
                role_slug="backend-engineer",
                top_k=5,
            )

            assert isinstance(result, RAGResult)
            assert isinstance(result.matches, list)

    @pytest.mark.asyncio
    async def test_retrieve_recommendations_respects_top_k(self, mock_session):
        """Test retrieve returns at most top_k recommendations."""
        service = RAGService(mock_session)

        # Mock many courses
        mock_courses = [
            {
                "course_id": str(i),
                "course_title": f"Python Course {i}",
                "subject": "Programming",
                "url": f"http://test.com/{i}",
            }
            for i in range(100)
        ]

        with patch.object(service, "_load_courses", return_value=mock_courses):
            result = await service.retrieve_recommendations(
                assessment_id="test-123",
                role_slug="backend-engineer",
                top_k=5,
            )

            assert len(result.matches) <= 5


class TestRAGServiceFallback:
    """Tests for RAG fallback behavior."""

    @pytest.fixture
    def mock_session(self):
        """Mock database session."""
        session = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_empty_courses_returns_fallback(self, mock_session):
        """Test fallback when no courses loaded."""
        from src.domain.services.rag import RAGResult

        service = RAGService(mock_session)

        with patch.object(service, "_load_courses", return_value=[]):
            result = await service.retrieve_recommendations(
                assessment_id="test-123",
                role_slug="backend-engineer",
                top_k=5,
            )

            # Should return RAGResult (possibly with fallback/degraded)
            assert isinstance(result, RAGResult)

    @pytest.mark.asyncio
    async def test_no_matches_returns_degraded(self, mock_session):
        """Test degraded flag when no matching courses found."""
        service = RAGService(mock_session)

        # Courses with no relevant keywords
        with patch.object(
            service,
            "_load_courses",
            return_value=[
                {
                    "course_id": "1",
                    "course_title": "Cooking 101",
                    "subject": "Lifestyle",
                    "url": "http://test.com/1",
                },
            ],
        ):
            result = await service.retrieve_recommendations(
                assessment_id="test-123",
                role_slug="backend-engineer",
                top_k=5,
            )

            # Should be degraded since no matches
            assert result.degraded is True

    @pytest.mark.asyncio
    async def test_no_matches_without_fallback_returns_empty_non_degraded(self, mock_session):
        """No-fallback mode should return empty results without degraded flag."""
        service = RAGService(mock_session)

        with patch.object(
            service,
            "_load_courses",
            return_value=[
                {
                    "course_id": "1",
                    "course_title": "Cooking 101",
                    "subject": "Lifestyle",
                    "url": "http://test.com/1",
                },
            ],
        ):
            result = await service.retrieve_recommendations(
                assessment_id="test-123",
                role_slug="backend-engineer",
                top_k=5,
                enable_fallback=False,
            )

            assert result.degraded is False
            assert result.matches == []
