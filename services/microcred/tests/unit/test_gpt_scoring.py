"""
Unit tests for GPT Essay Scoring Service.

Story 2.2 AC: Unit tests mock GPT responses to validate rubric parsing.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.domain.services.gpt_scoring import (
    GPTEssayScoringService,
)
from src.infrastructure.db.models import (
    Assessment,
    AssessmentQuestionSnapshot,
    AssessmentResponse,
    AssessmentStatus,
    AsyncJob,
    JobStatus,
    JobType,
    QuestionTemplate,
    QuestionType,
    RoleCatalog,
    Score,
)
from src.libs.gpt_client import GPTResponse

# ============================================================================
# Mock GPT Client
# ============================================================================


class MockGPTClient:
    """Mock GPT client for testing."""

    def __init__(
        self,
        responses: list[GPTResponse] | None = None,
        should_fail: bool = False,
        fail_on_call: int | None = None,
    ):
        self.responses = responses or []
        self.should_fail = should_fail
        self.fail_on_call = fail_on_call
        self.call_count = 0
        self.calls: list[dict[str, Any]] = []

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> GPTResponse:
        self.call_count += 1
        self.calls.append({
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        })

        if self.should_fail:
            from src.libs.gpt_client import GPTClientError

            raise GPTClientError("Mocked GPT failure")

        if self.fail_on_call is not None and self.call_count == self.fail_on_call:
            from src.libs.gpt_client import GPTClientError

            raise GPTClientError(f"Mocked failure on call {self.call_count}")

        if self.call_count <= len(self.responses):
            return self.responses[self.call_count - 1]

        # Default response
        return GPTResponse(
            content=json.dumps({
                "scores": {
                    "relevance": 85,
                    "depth": 80,
                    "clarity": 90,
                    "completeness": 75,
                    "technical": 70,
                },
                "total_score": 80,
                "explanation": "Good essay with solid analysis.",
            }),
            model="gpt-4o-mini",
            latency_ms=150,
            prompt_tokens=200,
            completion_tokens=100,
            total_tokens=300,
            finish_reason="stop",
        )


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_gpt_client() -> MockGPTClient:
    """Create a mock GPT client with default responses."""
    return MockGPTClient()


@pytest.fixture
async def essay_role(db: AsyncSession) -> RoleCatalog:
    """Create a role for essay testing."""
    role = RoleCatalog(
        slug=f"essay-role-{uuid4().hex[:8]}",
        name="Essay Test Role",
        description="Role for GPT scoring tests",
    )
    db.add(role)
    await db.commit()
    return role


@pytest.fixture
async def essay_assessment(
    db: AsyncSession,
    essay_role: RoleCatalog,
) -> tuple[Assessment, AsyncJob]:
    """Create an assessment with essay questions and responses."""
    # Create essay question template
    essay_q = QuestionTemplate(
        role_slug=essay_role.slug,
        sequence=1,
        question_type=QuestionType.ESSAY,
        prompt="Jelaskan konsep Machine Learning dan berikan contoh penerapannya.",
        metadata_={"category": "AI", "difficulty": "medium"},
        version=1,
        is_active=True,
    )
    db.add(essay_q)
    await db.flush()

    # Create assessment
    assessment = Assessment(
        id=str(uuid4()),
        owner_id=f"test-user-{uuid4().hex[:8]}",
        role_slug=essay_role.slug,
        status=AssessmentStatus.SUBMITTED,
        expires_at=datetime.now(UTC),
    )
    db.add(assessment)
    await db.flush()

    # Create question snapshot
    snapshot = AssessmentQuestionSnapshot(
        id=str(uuid4()),
        assessment_id=assessment.id,
        question_template_id=essay_q.id,
        sequence=1,
        prompt=essay_q.prompt,
        question_type=QuestionType.ESSAY,
    )
    db.add(snapshot)
    await db.flush()

    # Create response
    response = AssessmentResponse(
        id=str(uuid4()),
        assessment_id=assessment.id,
        question_snapshot_id=snapshot.id,
        response_data={
            "answer": (
                "Machine Learning adalah cabang dari kecerdasan buatan yang "
                "memungkinkan sistem untuk belajar dari data. Contoh penerapannya "
                "termasuk pengenalan gambar, rekomendasi produk, dan deteksi spam."
            )
        },
    )
    db.add(response)

    # Create async job
    job = AsyncJob(
        id=str(uuid4()),
        assessment_id=assessment.id,
        job_type=JobType.GPT,
        status=JobStatus.QUEUED,
    )
    db.add(job)

    await db.commit()
    return assessment, job


@pytest.fixture
async def multi_essay_assessment(
    db: AsyncSession,
    essay_role: RoleCatalog,
) -> tuple[Assessment, AsyncJob]:
    """Create an assessment with multiple essay questions."""
    assessment = Assessment(
        id=str(uuid4()),
        owner_id=f"test-user-multi-{uuid4().hex[:8]}",
        role_slug=essay_role.slug,
        status=AssessmentStatus.SUBMITTED,
        expires_at=datetime.now(UTC),
    )
    db.add(assessment)
    await db.flush()

    # Create 3 essay questions with snapshots and responses
    for i in range(3):
        q = QuestionTemplate(
            role_slug=essay_role.slug,
            sequence=10 + i,  # Avoid sequence conflict
            question_type=QuestionType.ESSAY,
            prompt=f"Essay question {i + 1}",
            metadata_={"category": "General", "difficulty": "medium"},
            version=1,
            is_active=True,
        )
        db.add(q)
        await db.flush()

        snapshot = AssessmentQuestionSnapshot(
            id=str(uuid4()),
            assessment_id=assessment.id,
            question_template_id=q.id,
            sequence=i + 1,
            prompt=q.prompt,
            question_type=QuestionType.ESSAY,
        )
        db.add(snapshot)
        await db.flush()

        response = AssessmentResponse(
            id=str(uuid4()),
            assessment_id=assessment.id,
            question_snapshot_id=snapshot.id,
            response_data={"answer": f"This is my answer to question {i + 1}"},
        )
        db.add(response)

    job = AsyncJob(
        id=str(uuid4()),
        assessment_id=assessment.id,
        job_type=JobType.GPT,
        status=JobStatus.QUEUED,
    )
    db.add(job)

    await db.commit()
    return assessment, job


# ============================================================================
# Tests
# ============================================================================


class TestGPTEssayScoringService:
    """Tests for GPT essay scoring service."""

    @pytest.mark.asyncio
    async def test_score_single_essay_success(
        self,
        db: AsyncSession,
        essay_assessment: tuple[Assessment, AsyncJob],
    ):
        """AC1: GPT called with deterministic prompt for essay scoring."""
        assessment, job = essay_assessment
        mock_client = MockGPTClient()

        service = GPTEssayScoringService(
            session=db,
            gpt_client=mock_client,
        )

        result = await service.score_assessment_essays(
            assessment_id=assessment.id,
            job_id=job.id,
        )

        # Verify success
        assert result.status == "success"
        assert len(result.essay_scores) == 1
        assert result.failed_count == 0

        # Verify GPT was called
        assert mock_client.call_count == 1

        # Verify deterministic temperature
        assert mock_client.calls[0]["temperature"] == 0.0

    @pytest.mark.asyncio
    async def test_rubric_scores_parsed_correctly(
        self,
        db: AsyncSession,
        essay_assessment: tuple[Assessment, AsyncJob],
    ):
        """AC2: GPT response parsed into rubric metrics."""
        assessment, job = essay_assessment

        custom_response = GPTResponse(
            content=json.dumps({
                "scores": {
                    "relevance": 92,
                    "depth": 88,
                    "clarity": 95,
                    "completeness": 85,
                    "technical": 78,
                },
                "total_score": 87.6,
                "explanation": "Excellent understanding demonstrated.",
            }),
            model="gpt-4o-mini",
            latency_ms=120,
            prompt_tokens=180,
            completion_tokens=90,
            total_tokens=270,
            finish_reason="stop",
        )
        mock_client = MockGPTClient(responses=[custom_response])

        service = GPTEssayScoringService(
            session=db,
            gpt_client=mock_client,
        )

        result = await service.score_assessment_essays(
            assessment_id=assessment.id,
            job_id=job.id,
        )

        # Verify rubric scores parsed
        assert len(result.essay_scores) == 1
        score = result.essay_scores[0]

        assert score.rubric_scores["relevance"] == 92
        assert score.rubric_scores["depth"] == 88
        assert score.rubric_scores["clarity"] == 95
        assert score.rubric_scores["completeness"] == 85
        assert score.rubric_scores["technical"] == 78
        assert score.score == 88.3
        assert score.explanation == "Excellent understanding demonstrated."

    @pytest.mark.asyncio
    async def test_score_saved_to_database(
        self,
        db: AsyncSession,
        essay_assessment: tuple[Assessment, AsyncJob],
    ):
        """Verify essay scores are persisted to the Score table."""
        assessment, job = essay_assessment
        mock_client = MockGPTClient()

        service = GPTEssayScoringService(
            session=db,
            gpt_client=mock_client,
        )

        await service.score_assessment_essays(
            assessment_id=assessment.id,
            job_id=job.id,
        )

        # Verify score in database
        stmt = select(Score).where(Score.assessment_id == assessment.id)
        result = await db.execute(stmt)
        scores = result.scalars().all()

        assert len(scores) == 1
        assert scores[0].question_type == QuestionType.ESSAY
        assert scores[0].scoring_method == "gpt"
        assert "rubric_scores" in scores[0].rules_applied

    @pytest.mark.asyncio
    async def test_job_status_updated(
        self,
        db: AsyncSession,
        essay_assessment: tuple[Assessment, AsyncJob],
    ):
        """Verify job status is updated throughout scoring."""
        assessment, job = essay_assessment
        mock_client = MockGPTClient()

        service = GPTEssayScoringService(
            session=db,
            gpt_client=mock_client,
        )

        await service.score_assessment_essays(
            assessment_id=assessment.id,
            job_id=job.id,
        )

        # Refresh job
        await db.refresh(job)

        assert job.status == JobStatus.COMPLETED
        assert job.started_at is not None
        assert job.completed_at is not None
        assert job.attempts == 1

    @pytest.mark.asyncio
    async def test_gpt_failure_marks_job_failed(
        self,
        db: AsyncSession,
        essay_assessment: tuple[Assessment, AsyncJob],
    ):
        """AC4: On GPT failure, fallback scoring is used and assessment is degraded."""
        assessment, job = essay_assessment
        mock_client = MockGPTClient(should_fail=True)

        service = GPTEssayScoringService(
            session=db,
            gpt_client=mock_client,
        )

        result = await service.score_assessment_essays(
            assessment_id=assessment.id,
            job_id=job.id,
        )

        # Verify partial status with fallback
        assert result.status == "partial"
        assert result.failed_count > 0
        assert result.fallback_count == result.failed_count
        assert result.hard_failed_count == 0
        assert len(result.essay_scores) == 1
        assert result.essay_scores[0].scoring_method == "rule_fallback"

        # Refresh and verify degraded
        await db.refresh(assessment)
        await db.refresh(job)
        assert job.status == JobStatus.COMPLETED
        assert job.error_payload["fallback_count"] == result.fallback_count
        assert assessment.degraded is True

    @pytest.mark.asyncio
    async def test_partial_failure_continues(
        self,
        db: AsyncSession,
        multi_essay_assessment: tuple[Assessment, AsyncJob],
    ):
        """AC3: Partial failures don't stop other essays from scoring."""
        assessment, job = multi_essay_assessment

        # Fail on second call only
        mock_client = MockGPTClient(fail_on_call=2)

        service = GPTEssayScoringService(
            session=db,
            gpt_client=mock_client,
        )

        result = await service.score_assessment_essays(
            assessment_id=assessment.id,
            job_id=job.id,
        )

        # Should have partial success with fallback replacing failed GPT attempt
        assert result.status == "partial"
        assert len(result.essay_scores) == 3
        assert result.failed_count == 1
        assert result.fallback_count == 1
        assert result.hard_failed_count == 0

    @pytest.mark.asyncio
    async def test_empty_essay_gets_zero_score(
        self,
        db: AsyncSession,
        essay_role: RoleCatalog,
    ):
        """Empty essay responses get zero score without calling GPT."""
        # Create assessment with empty essay
        assessment = Assessment(
            id=str(uuid4()),
            owner_id=f"test-empty-{uuid4().hex[:8]}",
            role_slug=essay_role.slug,
            status=AssessmentStatus.SUBMITTED,
            expires_at=datetime.now(UTC),
        )
        db.add(assessment)
        await db.flush()

        q = QuestionTemplate(
            role_slug=essay_role.slug,
            sequence=100,
            question_type=QuestionType.ESSAY,
            prompt="Empty question",
            metadata_={"category": "Test", "difficulty": "easy"},
            version=1,
            is_active=True,
        )
        db.add(q)
        await db.flush()

        snapshot = AssessmentQuestionSnapshot(
            id=str(uuid4()),
            assessment_id=assessment.id,
            question_template_id=q.id,
            sequence=1,
            prompt=q.prompt,
            question_type=QuestionType.ESSAY,
        )
        db.add(snapshot)
        await db.flush()

        response = AssessmentResponse(
            id=str(uuid4()),
            assessment_id=assessment.id,
            question_snapshot_id=snapshot.id,
            response_data={"answer": ""},  # Empty answer
        )
        db.add(response)

        job = AsyncJob(
            id=str(uuid4()),
            assessment_id=assessment.id,
            job_type=JobType.GPT,
            status=JobStatus.QUEUED,
        )
        db.add(job)
        await db.commit()

        mock_client = MockGPTClient()
        service = GPTEssayScoringService(
            session=db,
            gpt_client=mock_client,
        )

        result = await service.score_assessment_essays(
            assessment_id=assessment.id,
            job_id=job.id,
        )

        # GPT should not be called for empty answers
        assert mock_client.call_count == 0
        assert len(result.essay_scores) == 1
        assert result.essay_scores[0].score == 0.0

    @pytest.mark.asyncio
    async def test_non_informative_essay_gets_zero_score(
        self,
        db: AsyncSession,
        essay_assessment: tuple[Assessment, AsyncJob],
    ):
        """Very short/non-informative essay like 'aaaa' should score zero."""
        assessment, job = essay_assessment

        response_stmt = (
            select(AssessmentResponse)
            .join(
                AssessmentQuestionSnapshot,
                AssessmentQuestionSnapshot.id == AssessmentResponse.question_snapshot_id,
            )
            .where(AssessmentQuestionSnapshot.assessment_id == assessment.id)
        )
        response = (await db.execute(response_stmt)).scalar_one()
        response.response_data = {"answer": "aaaa"}
        await db.commit()

        mock_client = MockGPTClient()
        service = GPTEssayScoringService(
            session=db,
            gpt_client=mock_client,
        )

        result = await service.score_assessment_essays(
            assessment_id=assessment.id,
            job_id=job.id,
        )

        assert result.status == "success"
        assert len(result.essay_scores) == 1
        assert result.essay_scores[0].score == 0.0
        assert result.essay_scores[0].scoring_method == "rule"
        # Should skip GPT call entirely for non-informative answers.
        assert mock_client.call_count == 0

    @pytest.mark.asyncio
    async def test_no_essays_returns_success(
        self,
        db: AsyncSession,
        essay_role: RoleCatalog,
    ):
        """Assessment with no essays returns success with empty scores."""
        assessment = Assessment(
            id=str(uuid4()),
            owner_id=f"test-no-essay-{uuid4().hex[:8]}",
            role_slug=essay_role.slug,
            status=AssessmentStatus.SUBMITTED,
            expires_at=datetime.now(UTC),
        )
        db.add(assessment)

        job = AsyncJob(
            id=str(uuid4()),
            assessment_id=assessment.id,
            job_type=JobType.GPT,
            status=JobStatus.QUEUED,
        )
        db.add(job)
        await db.commit()

        mock_client = MockGPTClient()
        service = GPTEssayScoringService(
            session=db,
            gpt_client=mock_client,
        )

        result = await service.score_assessment_essays(
            assessment_id=assessment.id,
            job_id=job.id,
        )

        assert result.status == "success"
        assert len(result.essay_scores) == 0
        assert mock_client.call_count == 0


class TestGPTResponseParsing:
    """Tests for GPT response parsing edge cases."""

    @pytest.mark.asyncio
    async def test_parse_markdown_json_response(
        self,
        db: AsyncSession,
        essay_assessment: tuple[Assessment, AsyncJob],
    ):
        """Handle GPT responses wrapped in markdown code blocks."""
        assessment, job = essay_assessment

        markdown_response = GPTResponse(
            content="""```json
{
  "scores": {
    "relevance": 85,
    "depth": 80,
    "clarity": 90,
    "completeness": 75,
    "technical": 70
  },
  "total_score": 80,
  "explanation": "Good essay"
}
```""",
            model="gpt-4o-mini",
            latency_ms=100,
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            finish_reason="stop",
        )
        mock_client = MockGPTClient(responses=[markdown_response])

        service = GPTEssayScoringService(
            session=db,
            gpt_client=mock_client,
        )

        result = await service.score_assessment_essays(
            assessment_id=assessment.id,
            job_id=job.id,
        )

        assert result.status == "success"
        assert len(result.essay_scores) == 1
        assert result.essay_scores[0].score == 80.75

    @pytest.mark.asyncio
    async def test_parse_json_with_text_wrapper(
        self,
        db: AsyncSession,
        essay_assessment: tuple[Assessment, AsyncJob],
    ):
        """Handle GPT responses where JSON is wrapped by plain text."""
        assessment, job = essay_assessment

        wrapped_response = GPTResponse(
            content=(
                "Sure, here is the evaluation:\\n"
                '{"scores":{"relevance":80,"depth":70,"clarity":75,'
                '"completeness":72,"technical":68},"explanation":"ok"}'
            ),
            model="gpt-4o-mini",
            latency_ms=100,
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            finish_reason="stop",
        )
        mock_client = MockGPTClient(responses=[wrapped_response])

        service = GPTEssayScoringService(
            session=db,
            gpt_client=mock_client,
        )

        result = await service.score_assessment_essays(
            assessment_id=assessment.id,
            job_id=job.id,
        )

        assert result.status == "success"
        assert len(result.essay_scores) == 1

    @pytest.mark.asyncio
    async def test_parse_unterminated_json_response_with_recovery(
        self,
        db: AsyncSession,
        essay_assessment: tuple[Assessment, AsyncJob],
    ):
        """Unterminated JSON should be recovered before falling back."""
        assessment, job = essay_assessment

        truncated_response = GPTResponse(
            content=(
                '{"scores":{"relevance":80,"depth":70,"clarity":75,'
                '"completeness":72,"technical":68},"explanation":"ok"'
            ),
            model="gpt-4o-mini",
            latency_ms=100,
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            finish_reason="stop",
        )
        mock_client = MockGPTClient(responses=[truncated_response])

        service = GPTEssayScoringService(
            session=db,
            gpt_client=mock_client,
        )

        result = await service.score_assessment_essays(
            assessment_id=assessment.id,
            job_id=job.id,
        )

        assert result.status == "success"
        assert result.fallback_count == 0
        assert result.parse_recovery_count == 1
        assert len(result.essay_scores) == 1
        assert result.essay_scores[0].parse_recovery_used is True
        assert result.essay_scores[0].parse_attempt_count > 1
        assert result.retry_used_count == 0

    @pytest.mark.asyncio
    async def test_parse_failure_retries_once_and_succeeds(
        self,
        db: AsyncSession,
        essay_assessment: tuple[Assessment, AsyncJob],
    ):
        """Invalid first response should trigger one JSON-only retry before success."""
        assessment, job = essay_assessment

        invalid_response = GPTResponse(
            content="I think this answer deserves around 80 points.",
            model="gpt-4o-mini",
            latency_ms=100,
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            finish_reason="stop",
        )
        valid_response = GPTResponse(
            content=json.dumps({
                "scores": {
                    "relevance": 80,
                    "depth": 75,
                    "clarity": 78,
                    "completeness": 74,
                    "technical": 72,
                },
                "total_score": 75.8,
                "explanation": "Adequate response with moderate technical depth.",
            }),
            model="gpt-4o-mini",
            latency_ms=100,
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            finish_reason="stop",
        )
        mock_client = MockGPTClient(responses=[invalid_response, valid_response])

        service = GPTEssayScoringService(
            session=db,
            gpt_client=mock_client,
        )

        result = await service.score_assessment_essays(
            assessment_id=assessment.id,
            job_id=job.id,
        )

        assert result.status == "success"
        assert result.failed_count == 0
        assert result.fallback_count == 0
        assert result.retry_used_count == 1
        assert mock_client.call_count == 2
        assert len(result.essay_scores) == 1
        assert result.essay_scores[0].retry_used is True
        assert result.essay_scores[0].retry_count == 1

    @pytest.mark.asyncio
    async def test_parse_error_count_recorded_on_unrecoverable_json(
        self,
        db: AsyncSession,
        essay_assessment: tuple[Assessment, AsyncJob],
    ):
        """Unrecoverable parse errors should increment parse_error_count and use fallback."""
        assessment, job = essay_assessment

        invalid_response = GPTResponse(
            content="This is not JSON.",
            model="gpt-4o-mini",
            latency_ms=100,
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            finish_reason="stop",
        )
        retry_invalid_response = GPTResponse(
            content="Still not valid JSON output.",
            model="gpt-4o-mini",
            latency_ms=100,
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            finish_reason="stop",
        )
        mock_client = MockGPTClient(responses=[invalid_response, retry_invalid_response])

        service = GPTEssayScoringService(
            session=db,
            gpt_client=mock_client,
        )

        result = await service.score_assessment_essays(
            assessment_id=assessment.id,
            job_id=job.id,
        )

        assert result.status == "partial"
        assert result.fallback_count == 1
        assert result.parse_error_count == 1
        assert result.retry_used_count == 1
        assert result.hard_failed_count == 0
        assert mock_client.call_count == 2

        await db.refresh(job)
        assert job.error_payload["parse_error_count"] == 1
        assert job.error_payload["retry_used_count"] == 1
        assert job.error_payload["errors"][0]["is_parse_error"] == "true"
        assert job.error_payload["errors"][0]["retry_used"] == "true"

    @pytest.mark.asyncio
    async def test_clamp_scores_to_valid_range(
        self,
        db: AsyncSession,
        essay_assessment: tuple[Assessment, AsyncJob],
    ):
        """Scores outside 0-100 are clamped."""
        assessment, job = essay_assessment

        out_of_range_response = GPTResponse(
            content=json.dumps({
                "scores": {
                    "relevance": 150,  # Too high
                    "depth": -10,  # Too low
                    "clarity": 90,
                    "completeness": 75,
                    "technical": 70,
                },
                "total_score": 120,  # Too high
                "explanation": "Test",
            }),
            model="gpt-4o-mini",
            latency_ms=100,
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            finish_reason="stop",
        )
        mock_client = MockGPTClient(responses=[out_of_range_response])

        service = GPTEssayScoringService(
            session=db,
            gpt_client=mock_client,
        )

        result = await service.score_assessment_essays(
            assessment_id=assessment.id,
            job_id=job.id,
        )

        score = result.essay_scores[0]
        assert score.rubric_scores["relevance"] == 100  # Clamped to max
        assert score.rubric_scores["depth"] == 0  # Clamped to min
        assert score.score == 68.5  # Weighted + clamped
