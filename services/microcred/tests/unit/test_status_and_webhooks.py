"""
Unit tests for Story 2.3: Status Polling, Webhooks, and Idempotency.

Tests:
1. GET /assessments/{id}/status - returns stage progress
2. POST /assessments/{id}/webhook - registers webhook URL
3. POST /assessments/{id}/submit with idempotency key - prevents duplicates
4. Status progress calculation based on job states
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import select
from src.infrastructure.db.models import (
    Assessment,
    AssessmentStatus,
    AsyncJob,
    JobStatus,
    JobType,
)

from tests.utils import auth_headers, submit_with_payload


class TestStatusPolling:
    """Tests for GET /assessments/{id}/status endpoint."""

    def test_status_returns_stage_progress(
        self,
        test_client_with_questions: TestClient,
    ) -> None:
        """Test that status endpoint returns correct stage progress."""
        headers = auth_headers(user_id="student-status-1")

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

        submit_response = submit_with_payload(
            test_client_with_questions,
            assessment_id,
            questions,
            headers=headers,
        )
        assert submit_response.status_code == 200

        # Step 3: Get status
        response = test_client_with_questions.get(
            f"/assessments/{assessment_id}/status",
            headers=headers,
        )
        assert response.status_code == 200
        result = response.json()

        # Verify response structure
        assert result["assessment_id"] == assessment_id
        assert result["status"] == "submitted"
        assert "overall_progress" in result
        assert "stages" in result
        assert "jobs" in result

        # Verify stages (list of dicts with name, status, progress)
        stages = result["stages"]
        stage_dict = {s["name"]: s for s in stages}

        assert "rule_score" in stage_dict
        assert stage_dict["rule_score"]["status"] == "completed"
        assert stage_dict["rule_score"]["percentage"] == 100.0

        # GPT, RAG, and fusion should be pending since jobs were queued
        assert "gpt" in stage_dict
        assert "rag" in stage_dict
        assert "fusion" in stage_dict

    def test_status_not_found(
        self,
        test_client_with_questions: TestClient,
    ) -> None:
        """Test that status returns 404 for non-existent assessment."""
        headers = auth_headers(user_id="student-status-2")

        response = test_client_with_questions.get(
            f"/assessments/{uuid.uuid4()}/status",
            headers=headers,
        )
        assert response.status_code == 404

    def test_status_not_owned(
        self,
        test_client_with_questions: TestClient,
    ) -> None:
        """Test that status returns 403 for assessment not owned by user."""
        # Create assessment as one user
        owner_headers = auth_headers(user_id="student-status-owner")

        response = test_client_with_questions.post(
            "/assessments/start",
            json={"role_slug": "backend-engineer"},
            headers=owner_headers,
        )
        assert response.status_code == 200
        assessment_id = response.json()["assessment_id"]

        # Try to get status as another user
        other_headers = auth_headers(user_id="student-status-other")

        response = test_client_with_questions.get(
            f"/assessments/{assessment_id}/status",
            headers=other_headers,
        )
        assert response.status_code == 403


class TestWebhookRegistration:
    """Tests for POST /assessments/{id}/webhook endpoint."""

    def test_register_webhook_success(
        self,
        test_client_with_questions: TestClient,
        event_loop,
    ) -> None:
        """Test successful webhook URL registration."""
        headers = auth_headers(user_id="student-webhook-1")

        # Start an assessment
        response = test_client_with_questions.post(
            "/assessments/start",
            json={"role_slug": "backend-engineer"},
            headers=headers,
        )
        assert response.status_code == 200
        assessment_id = response.json()["assessment_id"]

        # Register webhook
        webhook_url = "https://example.com/webhook/callback"
        response = test_client_with_questions.post(
            f"/assessments/{assessment_id}/webhook",
            json={"webhook_url": webhook_url},
            headers=headers,
        )
        assert response.status_code == 200
        result = response.json()

        assert result["assessment_id"] == assessment_id
        assert result["webhook_url"] == webhook_url
        assert "registered_at" in result

        # Verify in DB
        session_factory = test_client_with_questions.session_factory

        async def verify_webhook():
            async with session_factory() as session:
                stmt = select(Assessment).where(Assessment.id == assessment_id)
                result = await session.execute(stmt)
                assessment = result.scalar_one_or_none()
                assert assessment is not None
                assert assessment.webhook_url == webhook_url

        event_loop.run_until_complete(verify_webhook())

    def test_register_webhook_not_found(
        self,
        test_client_with_questions: TestClient,
    ) -> None:
        """Test webhook registration returns 404 for non-existent assessment."""
        headers = auth_headers(user_id="student-webhook-2")

        response = test_client_with_questions.post(
            f"/assessments/{uuid.uuid4()}/webhook",
            json={"webhook_url": "https://example.com/webhook"},
            headers=headers,
        )
        assert response.status_code == 404

    def test_register_webhook_not_owned(
        self,
        test_client_with_questions: TestClient,
    ) -> None:
        """Test webhook registration returns 403 for assessment not owned by user."""
        # Create assessment as one user
        owner_headers = auth_headers(user_id="student-webhook-owner")

        response = test_client_with_questions.post(
            "/assessments/start",
            json={"role_slug": "backend-engineer"},
            headers=owner_headers,
        )
        assert response.status_code == 200
        assessment_id = response.json()["assessment_id"]

        # Try to register webhook as another user
        other_headers = auth_headers(user_id="student-webhook-other")

        response = test_client_with_questions.post(
            f"/assessments/{assessment_id}/webhook",
            json={"webhook_url": "https://example.com/webhook"},
            headers=other_headers,
        )
        assert response.status_code == 403

    def test_register_webhook_invalid_url(
        self,
        test_client_with_questions: TestClient,
    ) -> None:
        """Test webhook registration validates URL format."""
        headers = auth_headers(user_id="student-webhook-invalid")

        # Start an assessment
        response = test_client_with_questions.post(
            "/assessments/start",
            json={"role_slug": "backend-engineer"},
            headers=headers,
        )
        assert response.status_code == 200
        assessment_id = response.json()["assessment_id"]

        # Try invalid URL
        response = test_client_with_questions.post(
            f"/assessments/{assessment_id}/webhook",
            json={"webhook_url": "not-a-valid-url"},
            headers=headers,
        )
        assert response.status_code == 422  # Validation error


class TestIdempotencyKey:
    """Tests for idempotency key enforcement on submissions."""

    def test_idempotency_key_prevents_duplicate(
        self,
        test_client_with_questions: TestClient,
    ) -> None:
        """Test that duplicate idempotency key returns 409."""
        headers = auth_headers(user_id="student-idemp-1")

        # Start first assessment
        response = test_client_with_questions.post(
            "/assessments/start",
            json={"role_slug": "backend-engineer"},
            headers=headers,
        )
        assert response.status_code == 200
        first = response.json()
        assessment_id_1 = first["assessment_id"]
        questions_1 = first["questions"]

        # Submit first assessment with idempotency key
        idempotency_key = f"submit-key-{uuid.uuid4()}"
        headers_with_key = {**headers, "Idempotency-Key": idempotency_key}

        response = submit_with_payload(
            test_client_with_questions,
            assessment_id_1,
            questions_1,
            headers=headers_with_key,
        )
        assert response.status_code == 200

        # Start second assessment
        response = test_client_with_questions.post(
            "/assessments/start",
            json={"role_slug": "backend-engineer"},
            headers=headers,
        )
        assert response.status_code == 200
        second = response.json()
        assessment_id_2 = second["assessment_id"]
        questions_2 = second["questions"]

        # Try to submit second assessment with same idempotency key
        response = submit_with_payload(
            test_client_with_questions,
            assessment_id_2,
            questions_2,
            headers=headers_with_key,
        )
        assert response.status_code == 409
        assert "idempotency" in response.json()["detail"].lower()

    def test_submit_without_idempotency_key_works(
        self,
        test_client_with_questions: TestClient,
    ) -> None:
        """Test that submissions without idempotency key still work."""
        headers = auth_headers(user_id="student-idemp-2")

        # Start assessment
        response = test_client_with_questions.post(
            "/assessments/start",
            json={"role_slug": "backend-engineer"},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assessment_id = data["assessment_id"]
        questions = data["questions"]

        # Submit without idempotency key (should work)
        response = submit_with_payload(
            test_client_with_questions,
            assessment_id,
            questions,
            headers=headers,
        )
        assert response.status_code == 200


class TestStatusProgressCalculation:
    """Tests for status progress calculation based on job states."""

    def test_progress_with_completed_jobs(
        self,
        test_client_with_questions: TestClient,
        event_loop,
    ) -> None:
        """Test that progress increases when jobs complete."""
        headers = auth_headers(user_id="student-progress-1")

        # Start and submit assessment
        response = test_client_with_questions.post(
            "/assessments/start",
            json={"role_slug": "backend-engineer"},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assessment_id = data["assessment_id"]
        questions = data["questions"]

        session_factory = test_client_with_questions.session_factory
        submit_response = submit_with_payload(
            test_client_with_questions,
            assessment_id,
            questions,
            headers=headers,
        )
        assert submit_response.status_code == 200

        # Manually complete GPT job
        async def complete_gpt_job():
            async with session_factory() as session:
                stmt = select(AsyncJob).where(
                    AsyncJob.assessment_id == assessment_id,
                    AsyncJob.job_type == JobType.GPT.value,
                )
                result = await session.execute(stmt)
                job = result.scalar_one_or_none()
                if job:
                    job.status = JobStatus.COMPLETED.value
                    job.completed_at = datetime.now(UTC)
                    await session.commit()

        event_loop.run_until_complete(complete_gpt_job())

        # Get status and verify GPT stage shows completed
        response = test_client_with_questions.get(
            f"/assessments/{assessment_id}/status",
            headers=headers,
        )
        assert response.status_code == 200
        result = response.json()

        # Convert stages list to dict for easier assertion
        stages = result["stages"]
        stage_dict = {s["name"]: s for s in stages}

        # GPT stage should show as completed now
        assert stage_dict["gpt"]["status"] == "completed"
        assert stage_dict["gpt"]["percentage"] == 100.0

        # Overall progress should be higher now
        # rule_score (20%) + gpt (30%) = at least 50%
        assert result["overall_progress"] >= 50

    def test_status_uses_job_payload_progress(
        self,
        test_client_with_questions: TestClient,
        event_loop,
    ) -> None:
        """Stage and job progress should reflect explicit progress payload from async job."""
        headers = auth_headers(user_id="student-progress-payload")

        response = test_client_with_questions.post(
            "/assessments/start",
            json={"role_slug": "backend-engineer"},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assessment_id = data["assessment_id"]
        questions = data["questions"]

        submit_response = submit_with_payload(
            test_client_with_questions,
            assessment_id,
            questions,
            headers=headers,
        )
        assert submit_response.status_code == 200

        session_factory = test_client_with_questions.session_factory

        async def set_partial_progress() -> None:
            async with session_factory() as session:
                stmt = select(AsyncJob).where(
                    AsyncJob.assessment_id == assessment_id,
                    AsyncJob.job_type == JobType.GPT.value,
                )
                job = (await session.execute(stmt)).scalar_one_or_none()
                assert job is not None
                job.status = JobStatus.IN_PROGRESS.value
                job.started_at = datetime.now(UTC)
                job.payload = {
                    "progress": {
                        "percentage": 42.5,
                        "step": "Scored essay 1/3",
                    }
                }
                await session.commit()

        event_loop.run_until_complete(set_partial_progress())

        status_response = test_client_with_questions.get(
            f"/assessments/{assessment_id}/status",
            headers=headers,
        )
        assert status_response.status_code == 200
        result = status_response.json()

        stage_dict = {s["name"]: s for s in result["stages"]}
        assert stage_dict["gpt"]["status"] == "in_progress"
        assert stage_dict["gpt"]["percentage"] == 42.5

        jobs = {j["job_type"]: j for j in result["jobs"]}
        assert jobs["gpt"]["progress_percentage"] == 42.5
        assert jobs["gpt"]["progress_step"] == "Scored essay 1/3"

    def test_completed_assessment_reports_full_progress(
        self,
        test_client_with_questions: TestClient,
        event_loop,
    ) -> None:
        """Completed assessment should always return 100% overall progress."""
        headers = auth_headers(user_id="student-progress-terminal")

        response = test_client_with_questions.post(
            "/assessments/start",
            json={"role_slug": "backend-engineer"},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assessment_id = data["assessment_id"]
        questions = data["questions"]

        submit_response = submit_with_payload(
            test_client_with_questions,
            assessment_id,
            questions,
            headers=headers,
        )
        assert submit_response.status_code == 200

        session_factory = test_client_with_questions.session_factory

        async def mark_terminal_state() -> None:
            async with session_factory() as session:
                assessment = await session.get(Assessment, assessment_id)
                assert assessment is not None
                assessment.status = AssessmentStatus.COMPLETED

                stmt = select(AsyncJob).where(AsyncJob.assessment_id == assessment_id)
                jobs = list((await session.execute(stmt)).scalars().all())
                for job in jobs:
                    if job.job_type == JobType.GPT.value:
                        job.status = JobStatus.FAILED.value
                    else:
                        job.status = JobStatus.COMPLETED.value
                    job.completed_at = datetime.now(UTC)
                await session.commit()

        event_loop.run_until_complete(mark_terminal_state())

        status_response = test_client_with_questions.get(
            f"/assessments/{assessment_id}/status",
            headers=headers,
        )
        assert status_response.status_code == 200
        result = status_response.json()

        assert result["status"] == "completed"
        assert result["overall_progress"] == 100.0
