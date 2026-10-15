"""
Question Bank CRUD Endpoints
"""

from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.deps import get_db_session, require_roles
from src.api.schemas.questions import QuestionCreate, QuestionDetail, QuestionItem, QuestionUpdate
from src.infrastructure.db.models import QuestionTemplate

logger = structlog.get_logger()
router = APIRouter(prefix="/questions", tags=["questions"])


def _serialize_question(question: QuestionTemplate) -> dict[str, Any]:
    """Serialize QuestionTemplate to a JSON-ready dict."""
    metadata = question.metadata_
    if metadata is None:
        metadata = {}
    return {
        "id": question.id,
        "role_slug": question.role_slug,
        "sequence": question.sequence,
        "question_type": question.question_type,
        "prompt": question.prompt,
        "options": question.options,
        "difficulty": question.difficulty,
        "weight": question.weight,
        "correct_answer": question.correct_answer,
        "answer_key": question.answer_key,
        "model_answer": question.model_answer,
        "rubric": question.rubric,
        "expected_values": question.expected_values,
        "metadata": metadata,
        "version": question.version,
        "previous_version_id": question.previous_version_id,
        "is_active": question.is_active,
        "created_at": question.created_at,
        "updated_at": question.updated_at,
    }


@router.get("", response_model=list[QuestionItem])
async def list_questions(
    role_slug: str | None = None,
    db: AsyncSession = Depends(get_db_session),
) -> Any:
    """
    List all active questions, optionally filtered by role/track.
    """
    query = select(QuestionTemplate).where(QuestionTemplate.is_active.is_(True))
    if role_slug:
        query = query.where(QuestionTemplate.role_slug == role_slug)
    query = query.order_by(QuestionTemplate.role_slug, QuestionTemplate.sequence)

    result = await db.execute(query)
    questions = result.scalars().all()

    await logger.ainfo("list_questions", role_slug=role_slug, count=len(questions))
    return [_serialize_question(q) for q in questions]


@router.get("/{question_id}", response_model=QuestionDetail)
async def get_question(
    question_id: int,
    db: AsyncSession = Depends(get_db_session),
) -> Any:
    """
    Get a specific question by ID (including inactive).
    """
    result = await db.execute(select(QuestionTemplate).where(QuestionTemplate.id == question_id))
    question = result.scalar_one_or_none()

    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    await logger.ainfo("get_question", question_id=question_id, role_slug=question.role_slug)
    return _serialize_question(question)


@router.post("", response_model=QuestionDetail, status_code=status.HTTP_201_CREATED)
async def create_question(
    question_data: QuestionCreate,
    db: AsyncSession = Depends(get_db_session),
    _current_user: Any = Depends(require_roles(["admin"])),
) -> Any:
    """
    Create a new question (admin only).
    """
    # Check for duplicate sequence in role
    existing = await db.execute(
        select(QuestionTemplate).where(
            QuestionTemplate.role_slug == question_data.role_slug,
            QuestionTemplate.sequence == question_data.sequence,
            QuestionTemplate.is_active.is_(True),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Question with sequence {question_data.sequence} "
                f"already exists for {question_data.role_slug}"
            ),
        )

    # Convert options from pydantic models to dicts
    options_data = None
    if question_data.options:
        options_data = [opt.model_dump() for opt in question_data.options]

    new_question = QuestionTemplate(
        role_slug=question_data.role_slug,
        sequence=question_data.sequence,
        question_type=question_data.question_type,
        prompt=question_data.prompt,
        options=options_data,
        metadata_=question_data.metadata_,
        difficulty=question_data.difficulty,
        weight=question_data.weight or 1.0,
        correct_answer=question_data.correct_answer,
        answer_key=question_data.answer_key,
        model_answer=question_data.model_answer,
        rubric=question_data.rubric,
        expected_values=question_data.expected_values,
        version=1,
        is_active=True,
    )
    db.add(new_question)
    await db.commit()
    await db.refresh(new_question)

    await logger.ainfo(
        "create_question",
        question_id=new_question.id,
        role_slug=new_question.role_slug,
        sequence=new_question.sequence,
        admin_user=_current_user.user_id,
    )
    return _serialize_question(new_question)


@router.patch("/{question_id}", response_model=QuestionDetail)
async def update_question(
    question_id: int,
    question_data: QuestionUpdate,
    db: AsyncSession = Depends(get_db_session),
    _current_user: Any = Depends(require_roles(["admin"])),
) -> Any:
    """
    Update a question with versioning (admin only).
    Creates a new version and marks the old one inactive.
    """
    result = await db.execute(
        select(QuestionTemplate).where(
            QuestionTemplate.id == question_id, QuestionTemplate.is_active.is_(True)
        )
    )
    old_question = result.scalar_one_or_none()

    if not old_question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    # Mark old version as inactive
    old_question.is_active = False

    # Create new version with updated fields
    new_question = QuestionTemplate(
        role_slug=old_question.role_slug,
        sequence=(
            question_data.sequence if question_data.sequence is not None else old_question.sequence
        ),
        question_type=(
            question_data.question_type
            if question_data.question_type is not None
            else old_question.question_type
        ),
        prompt=question_data.prompt if question_data.prompt is not None else old_question.prompt,
        options=(
            [opt.model_dump() for opt in question_data.options]
            if question_data.options is not None
            else old_question.options
        ),
        metadata_=(
            question_data.metadata_
            if question_data.metadata_ is not None
            else old_question.metadata_
        ),
        difficulty=(
            question_data.difficulty
            if question_data.difficulty is not None
            else old_question.difficulty
        ),
        weight=question_data.weight if question_data.weight is not None else old_question.weight,
        correct_answer=(
            question_data.correct_answer
            if question_data.correct_answer is not None
            else old_question.correct_answer
        ),
        answer_key=(
            question_data.answer_key
            if question_data.answer_key is not None
            else old_question.answer_key
        ),
        model_answer=(
            question_data.model_answer
            if question_data.model_answer is not None
            else old_question.model_answer
        ),
        rubric=(question_data.rubric if question_data.rubric is not None else old_question.rubric),
        expected_values=(
            question_data.expected_values
            if question_data.expected_values is not None
            else old_question.expected_values
        ),
        version=old_question.version + 1,
        previous_version_id=old_question.id,
        is_active=True,
    )

    db.add(new_question)
    await db.commit()
    await db.refresh(new_question)

    await logger.ainfo(
        "update_question",
        old_id=question_id,
        new_id=new_question.id,
        version=new_question.version,
        admin_user=_current_user.user_id,
    )
    return _serialize_question(new_question)


@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_question(
    question_id: int,
    db: AsyncSession = Depends(get_db_session),
    _current_user: Any = Depends(require_roles(["admin"])),
) -> None:
    """
    Soft delete a question (admin only).
    """
    result = await db.execute(
        select(QuestionTemplate).where(
            QuestionTemplate.id == question_id, QuestionTemplate.is_active.is_(True)
        )
    )
    question = result.scalar_one_or_none()

    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    question.is_active = False
    await db.commit()

    await logger.ainfo(
        "delete_question",
        question_id=question_id,
        role_slug=question.role_slug,
        admin_user=_current_user.user_id,
    )
