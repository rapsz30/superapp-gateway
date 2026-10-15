"""
Unit tests for Story 2.1: Submission Finalization and Rule Scoring.

Tests:
1. POST /assessments/{id}/submit - success with scores
2. POST /assessments/{id}/submit - 404 not found
3. POST /assessments/{id}/submit - 403 not owned
4. POST /assessments/{id}/submit - 409 already submitted
5. POST /assessments/{id}/submit - degraded flag on missing responses
6. Rule scoring for theoretical questions
7. Async jobs creation (gpt, rag, fusion)
"""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select
from src.infrastructure.db.models import (
    Assessment,
    AssessmentStatus,
    AsyncJob,
    JobStatus,
    JobType,
)

from tests.utils import auth_headers, build_responses_payload


class TestSubmitAssessment:
    """Tests for POST /assessments/{id}/submit endpoint."""

    def test_submit_assessment_success(
        self,
        test_client_with_questions: TestClient,
    ) -> None:
        """Test successful assessment submission with rule-based scoring."""
        headers = auth_headers(user_id="student-submit-1")

        # Step 1: Start an assessment
        response = test_client_with_questions.post(
            "/assessments/start",
            json={"role_slug": "backend-engineer"},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assessment_id = data["assessment_id"]
        questions = data["questions"]

        payload = build_responses_payload(questions)
        response = test_client_with_questions.post(
            f"/assessments/{assessment_id}/submit",
            headers=headers,
            json=payload,
        )
        assert response.status_code == 200
        result = response.json()

        # Verify response structure
        assert result["assessment_id"] == assessment_id
        assert result["status"] == "submitted"
        assert result["degraded"] is False
        assert "submitted_at" in result
        assert "scores" in result
        assert "jobs_queued" in result

        # Verify scores structure
        scores = result["scores"]
        assert "theoretical" in scores
        assert "profile" in scores
        assert "essay" in scores
        assert scores["essay"]["status"] == "pending_gpt"

        # Verify async jobs were queued
        assert "rag" in result["jobs_queued"]
        assert "fusion" in result["jobs_queued"]

    def test_submit_assessment_invalid_question_id(
        self,
        test_client_with_questions: TestClient,
    ) -> None:
        """Submitting with an unknown question snapshot returns 400."""
        headers = auth_headers(user_id="student-submit-invalid")
        response = test_client_with_questions.post(
            "/assessments/start",
            json={"role_slug": "backend-engineer"},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assessment_id = data["assessment_id"]
        questions = data["questions"]

        payload = build_responses_payload(questions)
        payload["responses"][0]["question_id"] = "missing-question"
        response = test_client_with_questions.post(
            f"/assessments/{assessment_id}/submit",
            headers=headers,
            json=payload,
        )
        assert response.status_code == 400
        assert "Invalid question_id" in response.json()["detail"]

    def test_submit_assessment_not_found(
        self,
        test_client_with_questions: TestClient,
    ) -> None:
        """Test 404 when assessment doesn't exist."""
        headers = auth_headers(user_id="student-404")
        fake_id = str(uuid.uuid4())

        response = test_client_with_questions.post(
            f"/assessments/{fake_id}/submit",
            headers=headers,
        )
        assert response.status_code == 404
        assert "tidak ditemukan" in response.json()["detail"]

    def test_submit_assessment_not_owned(
        self,
        test_client_with_questions: TestClient,
    ) -> None:
        """Test 403 when student doesn't own the assessment."""
        # Start assessment as student-1
        headers1 = auth_headers(user_id="student-owner")
        response = test_client_with_questions.post(
            "/assessments/start",
            json={"role_slug": "backend-engineer"},
            headers=headers1,
        )
        assert response.status_code == 200
        assessment_id = response.json()["assessment_id"]

        # Try to submit as student-2
        headers2 = auth_headers(user_id="student-intruder")
        response = test_client_with_questions.post(
            f"/assessments/{assessment_id}/submit",
            headers=headers2,
        )
        assert response.status_code == 403
        assert "tidak memiliki akses" in response.json()["detail"]

    def test_submit_assessment_already_submitted(
        self,
        test_client_with_questions: TestClient,
        event_loop,
    ) -> None:
        """Test 409 when assessment already submitted."""
        headers = auth_headers(user_id="student-double")

        # Start assessment
        response = test_client_with_questions.post(
            "/assessments/start",
            json={"role_slug": "backend-engineer"},
            headers=headers,
        )
        assessment_id = response.json()["assessment_id"]

        # Mark as submitted directly in DB
        session_factory = test_client_with_questions.session_factory

        async def mark_submitted():
            async with session_factory() as session:
                assessment = await session.get(Assessment, assessment_id)
                assessment.status = AssessmentStatus.SUBMITTED
                await session.commit()

        event_loop.run_until_complete(mark_submitted())

        # Try to submit again
        response = test_client_with_questions.post(
            f"/assessments/{assessment_id}/submit",
            headers=headers,
        )
        assert response.status_code == 409
        assert "sudah di-submit" in response.json()["detail"]

    def test_submit_assessment_degraded_missing_responses(
        self,
        test_client_with_questions: TestClient,
    ) -> None:
        """Test degraded flag when some responses are missing."""
        headers = auth_headers(user_id="student-degraded")

        # Start assessment
        response = test_client_with_questions.post(
            "/assessments/start",
            json={"role_slug": "backend-engineer"},
            headers=headers,
        )
        assessment_id = response.json()["assessment_id"]
        # Don't add any responses - submit with missing data

        # Submit without responses (should be degraded)
        response = test_client_with_questions.post(
            f"/assessments/{assessment_id}/submit",
            headers=headers,
        )
        assert response.status_code == 200
        result = response.json()

        # Should be marked as degraded due to missing responses
        assert result["degraded"] is True


class TestRuleScoring:
    """Tests for rule-based scoring logic."""

    def test_theoretical_scoring(
        self,
        test_client_with_questions: TestClient,
    ) -> None:
        """Test theoretical question scores based on rule matching."""
        headers = auth_headers(user_id="student-theoretical")

        # Start assessment
        response = test_client_with_questions.post(
            "/assessments/start",
            json={"role_slug": "backend-engineer"},
            headers=headers,
        )
        data = response.json()
        assessment_id = data["assessment_id"]
        questions = data["questions"]

        payload = build_responses_payload(questions)
        response = test_client_with_questions.post(
            f"/assessments/{assessment_id}/submit",
            headers=headers,
            json=payload,
        )
        assert response.status_code == 200
        result = response.json()

        # Check theoretical scores exist
        theoretical_scores = result["scores"]["theoretical"]
        theoretical_count = sum(1 for q in questions if q["question_type"] == "theoretical")
        assert theoretical_scores["count"] == theoretical_count

    def test_profile_completeness_scoring(
        self,
        test_client_with_questions: TestClient,
    ) -> None:
        """Test profile question scores based on completeness."""
        headers = auth_headers(user_id="student-profile")

        # Start assessment
        response = test_client_with_questions.post(
            "/assessments/start",
            json={"role_slug": "backend-engineer"},
            headers=headers,
        )
        data = response.json()
        assessment_id = data["assessment_id"]
        questions = data["questions"]

        profile_questions = [q for q in questions if q["question_type"] == "profile"]
        payload = build_responses_payload(questions)
        response = test_client_with_questions.post(
            f"/assessments/{assessment_id}/submit",
            headers=headers,
            json=payload,
        )
        assert response.status_code == 200
        result = response.json()

        # Check profile scores
        profile_scores = result["scores"]["profile"]
        assert profile_scores["count"] == len(profile_questions)
        # All complete responses should get full score
        if profile_scores["count"] > 0:
            assert profile_scores["percentage"] == 100.0

    def test_profile_q7_project_checklist_weighted_scoring(
        self,
        test_client_with_questions: TestClient,
    ) -> None:
        """Q7 should use weighted sum from project_count + checklist contexts."""
        headers = auth_headers(user_id="student-profile-q7")
        start = test_client_with_questions.post(
            "/assessments/start",
            json={"role_slug": "backend-engineer"},
            headers=headers,
        )
        assert start.status_code == 200
        data = start.json()
        assessment_id = data["assessment_id"]
        questions = data["questions"]

        q7 = next(q for q in questions if q["question_type"] == "profile" and q["sequence"] == 7)

        payload = build_responses_payload(
            questions,
            overrides={
                q7["id"]: {
                    "project_count": 5,
                    "selected_options": ["kampus", "production"],
                    "value": "5",
                }
            },
        )
        submit = test_client_with_questions.post(
            f"/assessments/{assessment_id}/submit",
            headers=headers,
            json=payload,
        )
        assert submit.status_code == 200
        result = submit.json()

        q7_breakdown = next(
            item
            for item in result["scores"]["profile"]["breakdown"]
            if item["question_id"] == q7["id"]
        )
        assert q7_breakdown["max_score"] == 100.0
        # project_count=5 -> 40, contexts(kampus+production) -> 10+15, total=65
        assert q7_breakdown["score"] == 65.0

    def test_profile_expected_values_mismatch_scores_zero(
        self,
        test_client_with_questions: TestClient,
    ) -> None:
        """Mismatch against accepted_values (without custom override) should score zero."""
        headers = auth_headers(user_id="student-profile-mismatch")
        start = test_client_with_questions.post(
            "/assessments/start",
            json={"role_slug": "backend-engineer"},
            headers=headers,
        )
        assert start.status_code == 200
        data = start.json()
        assessment_id = data["assessment_id"]
        questions = data["questions"]

        q9 = next(q for q in questions if q["question_type"] == "profile" and q["sequence"] == 9)
        payload = build_responses_payload(
            questions,
            overrides={q9["id"]: {"value": "invalid-option"}},
        )

        submit = test_client_with_questions.post(
            f"/assessments/{assessment_id}/submit",
            headers=headers,
            json=payload,
        )
        assert submit.status_code == 200
        result = submit.json()

        q9_breakdown = next(
            item
            for item in result["scores"]["profile"]["breakdown"]
            if item["question_id"] == q9["id"]
        )
        assert q9_breakdown["score"] == 0.0
        assert q9_breakdown["explanation"] == "Profil terisi, tetapi tidak sesuai kriteria"

    def test_profile_allow_custom_value_still_scores_full(
        self,
        test_client_with_questions: TestClient,
    ) -> None:
        """Custom value should be accepted for profile questions that allow custom."""
        headers = auth_headers(user_id="student-profile-custom")
        start = test_client_with_questions.post(
            "/assessments/start",
            json={"role_slug": "backend-engineer"},
            headers=headers,
        )
        assert start.status_code == 200
        data = start.json()
        assessment_id = data["assessment_id"]
        questions = data["questions"]

        q8 = next(q for q in questions if q["question_type"] == "profile" and q["sequence"] == 8)
        payload = build_responses_payload(
            questions,
            overrides={q8["id"]: {"value": "rust, zig, custom-tech"}},
        )

        submit = test_client_with_questions.post(
            f"/assessments/{assessment_id}/submit",
            headers=headers,
            json=payload,
        )
        assert submit.status_code == 200
        result = submit.json()

        q8_breakdown = next(
            item
            for item in result["scores"]["profile"]["breakdown"]
            if item["question_id"] == q8["id"]
        )
        assert q8_breakdown["score"] == q8_breakdown["max_score"]
        assert q8_breakdown["explanation"] == "Profil terisi (custom value allowed)"


class TestAsyncJobCreation:
    """Tests for async job creation on submission."""

    def test_async_jobs_created_on_submit(
        self,
        test_client_with_questions: TestClient,
        event_loop,
    ) -> None:
        """Test that RAG and fusion jobs are created on submit."""
        headers = auth_headers(user_id="student-jobs")

        # Start assessment
        response = test_client_with_questions.post(
            "/assessments/start",
            json={"role_slug": "backend-engineer"},
            headers=headers,
        )
        data = response.json()
        assessment_id = data["assessment_id"]
        questions = data["questions"]

        payload = build_responses_payload(questions)
        response = test_client_with_questions.post(
            f"/assessments/{assessment_id}/submit",
            headers=headers,
            json=payload,
        )
        assert response.status_code == 200
        result = response.json()

        # RAG and fusion jobs should be queued
        assert "rag" in result["jobs_queued"]
        assert "fusion" in result["jobs_queued"]

        # Verify jobs in database
        session_factory = test_client_with_questions.session_factory

        async def verify_jobs():
            async with session_factory() as session:
                stmt = select(AsyncJob).where(AsyncJob.assessment_id == assessment_id)
                jobs = list((await session.execute(stmt)).scalars().all())
                return jobs

        jobs = event_loop.run_until_complete(verify_jobs())

        # Should have RAG and fusion jobs at minimum
        job_types = {job.job_type for job in jobs}
        assert JobType.RAG in job_types
        assert JobType.FUSION in job_types

        # All jobs should be queued
        for job in jobs:
            assert job.status == JobStatus.QUEUED

    def test_gpt_job_created_for_essays(
        self,
        test_client_with_questions: TestClient,
    ) -> None:
        """Test that GPT job is created when assessment has essay questions."""
        headers = auth_headers(user_id="student-essay")

        # Start assessment
        response = test_client_with_questions.post(
            "/assessments/start",
            json={"role_slug": "backend-engineer"},
            headers=headers,
        )
        data = response.json()
        assessment_id = data["assessment_id"]
        questions = data["questions"]

        # Check if there are essay questions
        has_essays = any(q["question_type"] == "essay" for q in questions)

        # Submit
        payload = build_responses_payload(questions)
        response = test_client_with_questions.post(
            f"/assessments/{assessment_id}/submit",
            headers=headers,
            json=payload,
        )
        assert response.status_code == 200
        result = response.json()

        # If there are essays, GPT job should be queued
        if has_essays:
            assert "gpt" in result["jobs_queued"]
