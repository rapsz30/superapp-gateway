"""
Question Bank Schemas for CRUD and Versioning
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator
from src.infrastructure.db.models import QuestionType


class OptionItem(BaseModel):
    """Single option for multiple choice questions"""

    id: str = Field(..., description="Option identifier (A, B, C, D)")
    text: str = Field(..., description="Option text")


class QuestionBase(BaseModel):
    """Base schema for question fields"""

    model_config = ConfigDict(protected_namespaces=())

    role_slug: str = Field(..., description="Role/track slug this question belongs to")
    sequence: int = Field(..., ge=1, description="Question order in assessment")
    question_type: QuestionType = Field(..., description="Type of question")
    prompt: str = Field(..., min_length=10, description="Question text")
    # Multiple choice options
    options: list[OptionItem] | None = Field(
        None, description="Options for multiple choice (theoretical) questions"
    )
    difficulty: str | None = Field(None, description="Difficulty level (easy/medium/hard)")
    weight: float | None = Field(None, ge=0.1, description="Score weight multiplier")
    correct_answer: str | None = Field(
        None, description="Correct answer (option ID for multiple choice)"
    )
    answer_key: str | None = Field(None, description="Reference answer for essays")
    model_answer: str | None = Field(None, description="Model answer for essays")
    rubric: dict[str, Any] | None = Field(
        None, description="Rubric weights and rules for GPT scoring"
    )
    expected_values: dict[str, Any] | None = Field(
        None, description="Accepted values for profile questions"
    )
    metadata_: Any = Field(
        default=None,
        alias="metadata",
        description="Optional metadata including rubric and rules",
    )

    @field_validator("metadata_", mode="before")
    @classmethod
    def convert_metadata(cls, v: Any) -> dict[str, Any] | None:
        """Convert SQLAlchemy JSON/MetaData to dict when possible."""
        if v is None:
            return None
        if isinstance(v, dict):
            return v
        if hasattr(v, "_data"):
            try:
                return dict(v._data)  # type: ignore[attr-defined]
            except Exception:
                return None
        try:
            return dict(v)
        except Exception:
            return None

    @field_serializer("metadata_", when_used="json")
    def serialize_metadata(self, v: Any) -> dict[str, Any] | None:
        """Serialize metadata to dict for JSON output"""
        if v is None:
            return None
        if isinstance(v, dict):
            return v
        # For SQLAlchemy JSON types that aren't iterable
        try:
            return dict(v)
        except (TypeError, ValueError):
            # If conversion fails, return None
            return None


class QuestionCreate(QuestionBase):
    """Schema for creating a new question"""

    pass


class QuestionUpdate(BaseModel):
    """Schema for updating an existing question (all fields optional)"""

    model_config = ConfigDict(protected_namespaces=())

    sequence: int | None = Field(None, ge=1)
    question_type: QuestionType | None = None
    prompt: str | None = Field(None, min_length=10)
    options: list[OptionItem] | None = None
    difficulty: str | None = None
    weight: float | None = Field(None, ge=0.1)
    correct_answer: str | None = None
    answer_key: str | None = None
    model_answer: str | None = None
    rubric: dict[str, Any] | None = None
    expected_values: dict[str, Any] | None = None
    metadata_: dict[str, Any] | None = Field(None, alias="metadata")


class QuestionDetail(QuestionBase):
    """Full question details including version and timestamps"""

    id: int
    version: int
    previous_version_id: int | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class QuestionItem(BaseModel):
    """Simplified question for list views"""

    id: int
    role_slug: str
    sequence: int
    question_type: QuestionType
    prompt: str
    version: int
    is_active: bool

    class Config:
        from_attributes = True
