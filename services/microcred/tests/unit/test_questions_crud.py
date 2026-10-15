"""
Unit tests for Question Bank CRUD endpoints
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.infrastructure.db.models import QuestionTemplate, QuestionType


@pytest.mark.asyncio
async def test_create_question_success(
    async_client: AsyncClient, admin_token: str, db: AsyncSession
) -> None:
    """Admin can create a new question"""
    response = await async_client.post(
        "/questions",
        json={
            "role_slug": "backend-engineer",
            "sequence": 100,  # Use high sequence to avoid conflict with seed data
            "question_type": "theoretical",
            "prompt": "Explain the difference between SQL and NoSQL databases",
            "metadata": {"rubric": {"max_score": 10}, "rules": ["min_words: 100"]},
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["role_slug"] == "backend-engineer"
    assert data["sequence"] == 100
    assert data["version"] == 1
    assert data["is_active"] is True
    assert data["previous_version_id"] is None

    # Verify in DB
    result = await db.execute(select(QuestionTemplate).where(QuestionTemplate.id == data["id"]))
    question = result.scalar_one()
    assert question.prompt == "Explain the difference between SQL and NoSQL databases"


@pytest.mark.asyncio
async def test_create_question_duplicate_sequence(
    async_client: AsyncClient, admin_token: str, db: AsyncSession
) -> None:
    """Cannot create question with duplicate sequence in same role"""
    # Create first question with sequence 101
    q1 = QuestionTemplate(
        role_slug="backend-engineer",
        sequence=101,
        question_type=QuestionType.THEORETICAL,
        prompt="First question",
        version=1,
        is_active=True,
    )
    db.add(q1)
    await db.commit()

    # Try to create duplicate
    response = await async_client.post(
        "/questions",
        json={
            "role_slug": "backend-engineer",
            "sequence": 101,
            "question_type": "essay",
            "prompt": "Second question",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_question_requires_admin(
    async_client: AsyncClient, student_token: str
) -> None:
    """Only admin can create questions"""
    response = await async_client.post(
        "/questions",
        json={
            "role_slug": "backend-engineer",
            "sequence": 1,
            "question_type": "theoretical",
            "prompt": "Test question",
        },
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_questions_all(async_client: AsyncClient, db: AsyncSession) -> None:
    """Can list all active questions"""
    q1 = QuestionTemplate(
        role_slug="backend-engineer",
        sequence=102,
        question_type=QuestionType.THEORETICAL,
        prompt="Question 1",
        version=1,
        is_active=True,
    )
    q2 = QuestionTemplate(
        role_slug="data-analyst",
        sequence=102,
        question_type=QuestionType.ESSAY,
        prompt="Question 2",
        version=1,
        is_active=True,
    )
    q3 = QuestionTemplate(
        role_slug="backend-engineer",
        sequence=103,
        question_type=QuestionType.PROFILE,
        prompt="Inactive question",
        version=1,
        is_active=False,
    )
    db.add_all([q1, q2, q3])
    await db.commit()

    response = await async_client.get("/questions")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2  # Only active questions
    assert data[0]["role_slug"] == "backend-engineer"
    assert data[1]["role_slug"] == "data-analyst"


@pytest.mark.asyncio
async def test_list_questions_filtered(async_client: AsyncClient, db: AsyncSession) -> None:
    """Can filter questions by role_slug"""
    q1 = QuestionTemplate(
        role_slug="backend-engineer",
        sequence=102,
        question_type=QuestionType.THEORETICAL,
        prompt="Backend question",
        version=1,
        is_active=True,
    )
    q2 = QuestionTemplate(
        role_slug="data-analyst",
        sequence=102,
        question_type=QuestionType.ESSAY,
        prompt="Data question",
        version=1,
        is_active=True,
    )
    db.add_all([q1, q2])
    await db.commit()

    response = await async_client.get("/questions?role_slug=backend-engineer")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["role_slug"] == "backend-engineer"


@pytest.mark.asyncio
async def test_get_question_success(async_client: AsyncClient, db: AsyncSession) -> None:
    """Can retrieve question by ID"""
    question = QuestionTemplate(
        role_slug="backend-engineer",
        sequence=102,
        question_type=QuestionType.THEORETICAL,
        prompt="Test question",
        metadata_={"rubric": {"max_score": 10}},
        version=1,
        is_active=True,
    )
    db.add(question)
    await db.commit()
    await db.refresh(question)

    response = await async_client.get(f"/questions/{question.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == question.id
    assert data["prompt"] == "Test question"
    assert data["metadata"]["rubric"]["max_score"] == 10


@pytest.mark.asyncio
async def test_get_question_not_found(async_client: AsyncClient) -> None:
    """Returns 404 for non-existent question"""
    response = await async_client.get("/questions/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_question_creates_version(
    async_client: AsyncClient, admin_token: str, db: AsyncSession
) -> None:
    """Updating a question creates a new version"""
    old_question = QuestionTemplate(
        role_slug="backend-engineer",
        sequence=102,
        question_type=QuestionType.THEORETICAL,
        prompt="Original question",
        version=1,
        is_active=True,
    )
    db.add(old_question)
    await db.commit()
    await db.refresh(old_question)
    old_id = old_question.id

    response = await async_client.patch(
        f"/questions/{old_id}",
        json={"prompt": "Updated question", "sequence": 2},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] != old_id
    assert data["version"] == 2
    assert data["previous_version_id"] == old_id
    assert data["prompt"] == "Updated question"
    assert data["sequence"] == 2
    assert data["is_active"] is True

    # Old version should be inactive
    await db.refresh(old_question)
    assert old_question.is_active is False


@pytest.mark.asyncio
async def test_update_question_requires_admin(
    async_client: AsyncClient, student_token: str, db: AsyncSession
) -> None:
    """Only admin can update questions"""
    question = QuestionTemplate(
        role_slug="backend-engineer",
        sequence=102,
        question_type=QuestionType.THEORETICAL,
        prompt="Test",
        version=1,
        is_active=True,
    )
    db.add(question)
    await db.commit()
    await db.refresh(question)

    response = await async_client.patch(
        f"/questions/{question.id}",
        json={"prompt": "Hacked"},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_question_soft_delete(
    async_client: AsyncClient, admin_token: str, db: AsyncSession
) -> None:
    """Deleting a question soft-deletes it"""
    question = QuestionTemplate(
        role_slug="backend-engineer",
        sequence=102,
        question_type=QuestionType.THEORETICAL,
        prompt="To be deleted",
        version=1,
        is_active=True,
    )
    db.add(question)
    await db.commit()
    await db.refresh(question)

    response = await async_client.delete(
        f"/questions/{question.id}", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 204

    # Question still exists but inactive
    await db.refresh(question)
    assert question.is_active is False

    # Not returned in list
    response = await async_client.get("/questions")
    assert response.status_code == 200
    assert len(response.json()) == 0


@pytest.mark.asyncio
async def test_delete_question_requires_admin(
    async_client: AsyncClient, student_token: str, db: AsyncSession
) -> None:
    """Only admin can delete questions"""
    question = QuestionTemplate(
        role_slug="backend-engineer",
        sequence=102,
        question_type=QuestionType.THEORETICAL,
        prompt="Test",
        version=1,
        is_active=True,
    )
    db.add(question)
    await db.commit()
    await db.refresh(question)

    response = await async_client.delete(
        f"/questions/{question.id}", headers={"Authorization": f"Bearer {student_token}"}
    )
    assert response.status_code == 403
