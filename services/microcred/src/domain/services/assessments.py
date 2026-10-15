from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.domain import User
from src.infrastructure.db.models import (
    Assessment,
    AssessmentQuestionSnapshot,
    AssessmentResponse,
    AssessmentStatus,
    QuestionTemplate,
    QuestionType,
    RoleCatalog,
)

if TYPE_CHECKING:
    from sqlalchemy import Select

logger = structlog.get_logger()

# Default question mix: 3 theoretical + 3 essay + 4 profile = 10 total
DEFAULT_QUESTION_MIX: dict[QuestionType, int] = {
    QuestionType.THEORETICAL: 3,
    QuestionType.ESSAY: 3,
    QuestionType.PROFILE: 4,
}

# Assessment expiry duration (15 minutes)
ASSESSMENT_EXPIRY_MINUTES = 15


class RoleNotFoundError(Exception):
    """Raised when requested role slug does not exist."""


class MissingQuestionTemplateError(Exception):
    """Raised when a role is not configured with question templates."""


@dataclass(slots=True)
class AssessmentQuestionPayload:
    id: str
    sequence: int
    question_type: str
    prompt: str
    difficulty: str | None
    options: list[dict] | None
    metadata: dict | None
    expected_values: dict | None
    response: dict | None


class AssessmentService:
    """Domain logic for assessment lifecycle operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def start_or_resume(self, *, user: User, role_slug: str) -> dict[str, Any]:
        role = await self._get_role(role_slug)
        if role is None:
            raise RoleNotFoundError(f"Role '{role_slug}' tidak ditemukan")

        assessment = await self._find_active_assessment(user_id=user.user_id, role_slug=role_slug)
        is_new = assessment is None
        if is_new:
            assessment = await self._create_assessment(
                user_id=user.user_id, role_slug=role_slug, role=role
            )

        questions = await self._build_questions_payload(assessment.id)

        # Log analytics event (AC4)
        await logger.ainfo(
            "assessment_started",
            event_type="assessment_start" if is_new else "assessment_resume",
            student_id=user.user_id,
            track_slug=role_slug,
            assessment_id=assessment.id,
            question_count=len(questions),
            expires_at=assessment.expires_at.isoformat() if assessment.expires_at else None,
        )

        return {
            "assessment_id": assessment.id,
            "status": assessment.status.value,
            "expires_at": assessment.expires_at.isoformat() if assessment.expires_at else None,
            "role": {
                "slug": role.slug,
                "name": role.name,
                "description": role.description,
                "question_count": len(questions),
            },
            "questions": [asdict(question) for question in questions],
        }

    async def _get_role(self, role_slug: str) -> RoleCatalog | None:
        stmt: Select[tuple[RoleCatalog]] = select(RoleCatalog).where(RoleCatalog.slug == role_slug)
        return await self.session.scalar(stmt)

    async def _find_active_assessment(self, *, user_id: str, role_slug: str) -> Assessment | None:
        stmt: Select[tuple[Assessment]] = (
            select(Assessment)
            .where(
                Assessment.owner_id == user_id,
                Assessment.role_slug == role_slug,
                Assessment.status.in_(AssessmentStatus.active_statuses()),
            )
            .order_by(Assessment.created_at.desc())
        )
        assessments = list((await self.session.execute(stmt)).scalars().all())
        for assessment in assessments:
            if not self._is_expired(assessment.expires_at):
                return assessment
        return None

    @staticmethod
    def _is_expired(expires_at: datetime | None) -> bool:
        if expires_at is None:
            return False
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        return datetime.now(UTC) >= expires_at

    async def _create_assessment(
        self, *, user_id: str, role_slug: str, role: RoleCatalog
    ) -> Assessment:
        templates = await self._get_question_templates(role_slug)
        if not templates:
            raise MissingQuestionTemplateError(
                f"Role '{role_slug}' belum memiliki question templates"
            )

        # Get question mix (use overrides from role if available)
        question_mix = self._get_question_mix(role)

        # Select questions by type according to mix
        selected_templates = self._select_questions_by_mix(templates, question_mix)

        # Calculate expiry time (15 minutes from now)
        expires_at = datetime.now(UTC) + timedelta(minutes=ASSESSMENT_EXPIRY_MINUTES)

        assessment = Assessment(
            owner_id=user_id,
            role_slug=role_slug,
            status=AssessmentStatus.DRAFT,
            expires_at=expires_at,
        )
        self.session.add(assessment)
        await self.session.flush()

        for template in selected_templates:
            metadata = template.metadata_ or {}
            if template.expected_values and "accepted_values" not in metadata:
                metadata = {
                    **metadata,
                    "accepted_values": template.expected_values.get(
                        "accepted_values", template.expected_values
                    ),
                }

            snapshot = AssessmentQuestionSnapshot(
                assessment_id=assessment.id,
                question_template_id=template.id,
                sequence=template.sequence,
                question_type=template.question_type,
                prompt=template.prompt,
                options=template.options,  # Include multiple choice options
                metadata_=metadata,
                difficulty=template.difficulty,
                weight=template.weight,
                correct_answer=template.correct_answer,
                answer_key=template.answer_key,
                model_answer=template.model_answer,
                rubric=template.rubric,
                expected_values=template.expected_values,
            )
            self.session.add(snapshot)

        await self.session.commit()
        await self.session.refresh(assessment)
        return assessment

    def _get_question_mix(self, role: RoleCatalog) -> dict[QuestionType, int]:
        """Get question mix from role overrides or use default."""
        if role.question_mix_overrides:
            return {
                QuestionType(k): v
                for k, v in role.question_mix_overrides.items()
                if k in [qt.value for qt in QuestionType]
            }
        return DEFAULT_QUESTION_MIX.copy()

    def _select_questions_by_mix(
        self, templates: list[QuestionTemplate], question_mix: dict[QuestionType, int]
    ) -> list[QuestionTemplate]:
        """Select questions according to type mix (AC2: 3 theoretical + 3 essay + 4 profile)."""
        selected: list[QuestionTemplate] = []

        for qtype, count in question_mix.items():
            type_templates = [t for t in templates if t.question_type == qtype and t.is_active]
            logger.info(
                f"DEBUG: Type={qtype.value}, Want={count}, Available={len(type_templates)}, "
                f"Sequences={[t.sequence for t in type_templates]}"
            )
            # Take up to 'count' questions of this type
            selected.extend(type_templates[:count])

        # Sort by sequence for consistent ordering
        selected.sort(key=lambda t: t.sequence)
        logger.info(
            f"DEBUG: Total selected={len(selected)}, Sequences={[t.sequence for t in selected]}"
        )
        return selected

    async def _get_question_templates(self, role_slug: str) -> list[QuestionTemplate]:
        stmt: Select[tuple[QuestionTemplate]] = (
            select(QuestionTemplate)
            .where(QuestionTemplate.role_slug == role_slug, QuestionTemplate.is_active.is_(True))
            .order_by(QuestionTemplate.sequence)
        )
        templates = list((await self.session.execute(stmt)).scalars().all())
        logger.info(
            f"DEBUG: Loaded {len(templates)} templates for role={role_slug}. "
            f"Sequences: {[t.sequence for t in templates]}"
        )
        return templates

    async def _build_questions_payload(self, assessment_id: str) -> list[AssessmentQuestionPayload]:
        stmt = (
            select(AssessmentQuestionSnapshot, AssessmentResponse)
            .join(
                AssessmentResponse,
                AssessmentResponse.question_snapshot_id == AssessmentQuestionSnapshot.id,
                isouter=True,
            )
            .where(AssessmentQuestionSnapshot.assessment_id == assessment_id)
            .order_by(AssessmentQuestionSnapshot.sequence)
        )
        rows = (await self.session.execute(stmt)).all()

        payloads: list[AssessmentQuestionPayload] = []
        seen_ids: set[str] = set()
        for snapshot, response in rows:
            if snapshot.id in seen_ids:
                continue
            seen_ids.add(snapshot.id)
            payloads.append(
                AssessmentQuestionPayload(
                    id=snapshot.id,
                    sequence=snapshot.sequence,
                    question_type=snapshot.question_type.value,
                    prompt=snapshot.prompt,
                    difficulty=snapshot.difficulty,
                    options=snapshot.options,
                    metadata=snapshot.metadata_ or {},
                    expected_values=snapshot.expected_values or {},
                    response=response.response_data if response else None,
                )
            )
        return payloads
