from __future__ import annotations

from datetime import UTC, datetime, timedelta

from src.infrastructure.db.models import Assessment

from tests.utils import auth_headers


def test_assessment_start_creates_payload(test_client_with_questions) -> None:
    response = test_client_with_questions.post(
        "/assessments/start",
        json={"role_slug": "backend-engineer"},
        headers=auth_headers(),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["role"]["slug"] == "backend-engineer"
    assert len(payload["questions"]) == 10


def test_assessment_start_resumes_existing(test_client_with_questions) -> None:
    first = test_client_with_questions.post(
        "/assessments/start",
        json={"role_slug": "backend-engineer"},
        headers=auth_headers(),
    )
    second = test_client_with_questions.post(
        "/assessments/start",
        json={"role_slug": "backend-engineer"},
        headers=auth_headers(),
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["assessment_id"] == second.json()["assessment_id"]


def test_assessment_start_unknown_role_returns_404(test_client_with_questions) -> None:
    response = test_client_with_questions.post(
        "/assessments/start",
        json={"role_slug": "unknown"},
        headers=auth_headers(),
    )
    assert response.status_code == 404


def test_assessment_has_expiry(test_client_with_questions) -> None:
    """AC3: Assessment should have expiry timestamp"""
    response = test_client_with_questions.post(
        "/assessments/start",
        json={"role_slug": "backend-engineer"},
        headers=auth_headers(),
    )
    assert response.status_code == 200
    payload = response.json()
    assert "expires_at" in payload
    assert payload["expires_at"] is not None


def test_assessment_question_mix(test_client_with_questions) -> None:
    """AC2: Should have 3 theoretical + 3 essay + 4 profile = 10 questions"""
    response = test_client_with_questions.post(
        "/assessments/start",
        json={"role_slug": "backend-engineer"},
        headers=auth_headers(),
    )
    assert response.status_code == 200
    questions = response.json()["questions"]
    assert len(questions) == 10

    # Count by type
    type_counts = {}
    for q in questions:
        qtype = q["question_type"]
        type_counts[qtype] = type_counts.get(qtype, 0) + 1

    # Verify mix: 3 theoretical + 3 essay + 4 profile
    assert type_counts.get("theoretical", 0) == 3
    assert type_counts.get("essay", 0) == 3
    assert type_counts.get("profile", 0) == 4


def test_assessment_start_skips_expired_active_assessment(
    test_client_with_questions,
    event_loop,
) -> None:
    headers = auth_headers(user_id="student-expired-active")

    first = test_client_with_questions.post(
        "/assessments/start",
        json={"role_slug": "backend-engineer"},
        headers=headers,
    )
    assert first.status_code == 200
    first_assessment_id = first.json()["assessment_id"]

    session_factory = test_client_with_questions.session_factory  # type: ignore[attr-defined]

    async def expire_assessment() -> None:
        async with session_factory() as session:
            assessment = await session.get(Assessment, first_assessment_id)
            assert assessment is not None
            assessment.expires_at = datetime.now(UTC) - timedelta(minutes=1)
            await session.commit()

    event_loop.run_until_complete(expire_assessment())

    second = test_client_with_questions.post(
        "/assessments/start",
        json={"role_slug": "backend-engineer"},
        headers=headers,
    )
    assert second.status_code == 200
    second_assessment_id = second.json()["assessment_id"]

    assert second_assessment_id != first_assessment_id
