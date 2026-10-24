from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class QuestionType(str, enum.Enum):
    THEORETICAL = "theoretical"
    ESSAY = "essay"
    PROFILE = "profile"


class AssessmentStatus(str, enum.Enum):
    """Assessment workflow status enum.

    Note: Must use name='assessment_status' in Enum() to match database enum type.
    """

    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"  # Awaiting async scoring
    COMPLETED = "completed"
    FAILED = "failed"

    @classmethod
    def active_statuses(cls) -> tuple[AssessmentStatus, ...]:
        return (cls.DRAFT, cls.IN_PROGRESS)


class JobType(str, enum.Enum):
    GPT = "gpt"
    RAG = "rag"
    FUSION = "fusion"


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class UserStatus(str, enum.Enum):
    """User account status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class UserRole(str, enum.Enum):
    """User role enum matching auth.Role."""

    STUDENT = "student"
    ADVISOR = "advisor"
    ADMIN = "admin"


class UserModel(Base):
    """SQLAlchemy model for users table."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # Identitas mahasiswa (nullable agar akun lama tetap valid)
    nim: Mapped[str | None] = mapped_column(String(32), unique=True, nullable=True, index=True)
    faculty: Mapped[str | None] = mapped_column(String(100), nullable=True)
    study_program: Mapped[str | None] = mapped_column(String(100), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", values_callable=lambda e: [x.value for x in e]),
        default=UserRole.STUDENT,
        nullable=False,
    )
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, name="user_status", values_callable=lambda e: [x.value for x in e]),
        default=UserStatus.ACTIVE,
        nullable=False,
    )
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<UserModel(id={self.id}, email={self.email}, role={self.role.value})>"


class RoleCatalog(Base):
    __tablename__ = "role_catalog"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    skill_focus_tags: Mapped[list[str] | None] = mapped_column(JSON)
    question_mix_overrides: Mapped[dict[str, int] | None] = mapped_column(JSON)
    advanced_threshold_pct: Mapped[float] = mapped_column(Float, nullable=False, default=70.0)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    question_templates: Mapped[list[QuestionTemplate]] = relationship(
        back_populates="role",
        cascade="all,delete",
    )


class QuestionTemplate(Base):
    __tablename__ = "question_templates"
    __table_args__ = (UniqueConstraint("role_slug", "sequence", name="uq_question_sequence"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role_slug: Mapped[str] = mapped_column(
        ForeignKey("role_catalog.slug", ondelete="CASCADE"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    question_type: Mapped[QuestionType] = mapped_column(
        Enum(QuestionType, name="question_type", values_callable=lambda e: [x.value for x in e]),
        nullable=False,
    )
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    # Multiple choice options: [{"id": "A", "text": "..."}, ...]
    options: Mapped[list[dict] | None] = mapped_column(JSON)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON)
    difficulty: Mapped[str | None] = mapped_column(String(32), default="medium")
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    # Correct answer for multiple choice (e.g., "A", "B", "C", "D")
    correct_answer: Mapped[str | None] = mapped_column(String(255))
    answer_key: Mapped[str | None] = mapped_column(Text)
    model_answer: Mapped[str | None] = mapped_column(Text)
    # Rubric for essay scoring with GPT
    rubric: Mapped[dict | None] = mapped_column(JSON)
    expected_values: Mapped[dict | None] = mapped_column(JSON)

    # Versioning and soft delete
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    previous_version_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    role: Mapped[RoleCatalog] = relationship(back_populates="question_templates")


class Assessment(Base):
    __tablename__ = "assessments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    role_slug: Mapped[str] = mapped_column(
        ForeignKey("role_catalog.slug", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[AssessmentStatus] = mapped_column(
        Enum(
            AssessmentStatus,
            name="assessment_status",
            values_callable=lambda enum: [e.value for e in enum],
        ),
        default=AssessmentStatus.DRAFT,
        nullable=False,
        index=True,
    )
    degraded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Story 2.3: Webhook and idempotency
    webhook_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(
        String(64), nullable=True, unique=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    role: Mapped[RoleCatalog] = relationship()
    question_snapshots: Mapped[list[AssessmentQuestionSnapshot]] = relationship(
        back_populates="assessment",
        cascade="all,delete-orphan",
        order_by="AssessmentQuestionSnapshot.sequence",
    )
    responses: Mapped[list[AssessmentResponse]] = relationship(
        back_populates="assessment", cascade="all,delete-orphan"
    )
    scores: Mapped[list[Score]] = relationship(
        back_populates="assessment", cascade="all,delete-orphan"
    )
    jobs: Mapped[list[AsyncJob]] = relationship(
        back_populates="assessment", cascade="all,delete-orphan"
    )
    recommendation: Mapped[Recommendation | None] = relationship(
        back_populates="assessment", cascade="all,delete-orphan", uselist=False
    )


class AssessmentQuestionSnapshot(Base):
    __tablename__ = "assessment_question_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    assessment_id: Mapped[str] = mapped_column(
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_template_id: Mapped[int | None] = mapped_column(
        ForeignKey("question_templates.id", ondelete="SET NULL"),
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    question_type: Mapped[QuestionType] = mapped_column(
        Enum(QuestionType, name="question_type", values_callable=lambda e: [x.value for x in e]),
        nullable=False,
    )
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    # Multiple choice options copied from template
    options: Mapped[list[dict] | None] = mapped_column(JSON)
    metadata_: Mapped[dict | None] = mapped_column("metadata_", JSON)
    difficulty: Mapped[str | None] = mapped_column(String(32), default="medium")
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    correct_answer: Mapped[str | None] = mapped_column(String(255))
    answer_key: Mapped[str | None] = mapped_column(Text)
    model_answer: Mapped[str | None] = mapped_column(Text)
    rubric: Mapped[dict | None] = mapped_column(JSON)
    expected_values: Mapped[dict | None] = mapped_column(JSON)

    assessment: Mapped[Assessment] = relationship(back_populates="question_snapshots")
    template: Mapped[QuestionTemplate | None] = relationship()
    responses: Mapped[list[AssessmentResponse]] = relationship(
        back_populates="question_snapshot",
        cascade="all,delete-orphan",
    )


class AssessmentResponse(Base):
    __tablename__ = "assessment_responses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    assessment_id: Mapped[str] = mapped_column(
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_snapshot_id: Mapped[str] = mapped_column(
        ForeignKey("assessment_question_snapshots.id", ondelete="CASCADE"),
        nullable=False,
    )
    response_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    assessment: Mapped[Assessment] = relationship(back_populates="responses")
    question_snapshot: Mapped[AssessmentQuestionSnapshot] = relationship(back_populates="responses")


class Score(Base):
    """Stores per-question scores from rule-based and GPT scoring."""

    __tablename__ = "scores"
    __table_args__ = (
        UniqueConstraint("assessment_id", "question_snapshot_id", name="uq_score_per_question"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    assessment_id: Mapped[str] = mapped_column(
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_snapshot_id: Mapped[str] = mapped_column(
        ForeignKey("assessment_question_snapshots.id", ondelete="CASCADE"),
        nullable=False,
    )
    question_type: Mapped[QuestionType] = mapped_column(
        Enum(QuestionType, name="question_type", values_callable=lambda e: [x.value for x in e]),
        nullable=False,
    )
    score: Mapped[float] = mapped_column(nullable=False)
    max_score: Mapped[float] = mapped_column(nullable=False, default=100.0)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    scoring_method: Mapped[str] = mapped_column(String(32), nullable=False)  # "rule" or "gpt"
    rules_applied: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    model_info: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # GPT model details
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    assessment: Mapped[Assessment] = relationship(back_populates="scores")
    question_snapshot: Mapped[AssessmentQuestionSnapshot] = relationship()


class AsyncJob(Base):
    """Tracks async processing jobs (GPT scoring, RAG, fusion)."""

    __tablename__ = "async_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    assessment_id: Mapped[str] = mapped_column(
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default=JobStatus.QUEUED.value, nullable=False, index=True
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    queued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    assessment: Mapped[Assessment] = relationship(back_populates="jobs")


# Story 3.1 & 3.2: Recommendations
class Recommendation(Base):
    """Stores fusion summary and overall recommendation for an assessment."""

    __tablename__ = "recommendations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    assessment_id: Mapped[str] = mapped_column(
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)  # Fusion narrative
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    degraded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rag_query: Mapped[str | None] = mapped_column(Text, nullable=True)  # Query used for RAG
    rag_traces: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # RAG debug info
    score_breakdown: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    processing_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    assessment: Mapped[Assessment] = relationship(back_populates="recommendation")
    items: Mapped[list[RecommendationItem]] = relationship(
        back_populates="recommendation",
        cascade="all,delete-orphan",
        order_by="RecommendationItem.rank",
    )


class RecommendationItem(Base):
    """Individual recommended credential/course from RAG retrieval."""

    __tablename__ = "recommendation_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    recommendation_id: Mapped[str] = mapped_column(
        ForeignKey("recommendations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 = top recommendation
    course_id: Mapped[str] = mapped_column(String(64), nullable=False)
    course_title: Mapped[str] = mapped_column(String(512), nullable=False)
    course_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    relevance_score: Mapped[float] = mapped_column(Float, nullable=False)
    match_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    course_metadata: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )  # "metadata" is reserved
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    recommendation: Mapped[Recommendation] = relationship(back_populates="items")


# Story 3.3: Feedback
class Feedback(Base):
    """Stores advisor/student feedback on recommendations."""

    __tablename__ = "feedbacks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    recommendation_id: Mapped[str] = mapped_column(
        ForeignKey("recommendations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_role: Mapped[str] = mapped_column(String(20), nullable=False)  # student, advisor
    rating_relevance: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5
    rating_acceptance: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5
    # Per-course relevance labels for recommendation quality evaluation (0-2 scale).
    item_ratings: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    track_slug: Mapped[str | None] = mapped_column(String(64), nullable=True)  # For analytics
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    recommendation: Mapped[Recommendation] = relationship()


__all__ = [
    "QuestionType",
    "AssessmentStatus",
    "JobType",
    "JobStatus",
    "UserStatus",
    "UserRole",
    "UserModel",
    "RoleCatalog",
    "QuestionTemplate",
    "Assessment",
    "AssessmentQuestionSnapshot",
    "AssessmentResponse",
    "Score",
    "AsyncJob",
    "Recommendation",
    "RecommendationItem",
    "Feedback",
]
