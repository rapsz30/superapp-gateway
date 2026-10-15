from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.deps import get_db_session, require_roles
from src.api.schemas.tracks import (
    TrackCreate,
    TrackDetail,
    TrackItem,
    TracksResponse,
    TrackUpdate,
)
from src.domain import User
from src.infrastructure.db.models import QuestionTemplate, RoleCatalog

if TYPE_CHECKING:
    from sqlalchemy import Select

router = APIRouter(prefix="/tracks", tags=["Tracks"])
logger = structlog.get_logger()


@router.get("", response_model=TracksResponse)
async def list_tracks(session: AsyncSession = Depends(get_db_session)) -> TracksResponse:
    """Return available planning tracks/roles along with question counts."""
    role_stmt: Select[tuple[RoleCatalog]] = (
        select(RoleCatalog).where(RoleCatalog.is_active == True).order_by(RoleCatalog.name)  # noqa: E712
    )
    roles = (await session.execute(role_stmt)).scalars().all()

    count_stmt = (
        select(QuestionTemplate.role_slug, func.count(QuestionTemplate.id))
        .where(QuestionTemplate.is_active == True)  # noqa: E712
        .group_by(QuestionTemplate.role_slug)
    )
    count_pairs = (await session.execute(count_stmt)).all()
    question_count_map = {slug: count for slug, count in count_pairs}

    items = [
        TrackItem(
            slug=role.slug,
            name=role.name,
            description=role.description,
            question_count=question_count_map.get(role.slug, 0),
        )
        for role in roles
    ]
    return TracksResponse(tracks=items)


@router.post("", response_model=TrackDetail, status_code=status.HTTP_201_CREATED)
async def create_track(
    payload: TrackCreate,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_roles(["admin"])),
) -> TrackDetail:
    """Create a new track (admin-only)."""
    # Check if slug already exists
    existing = await session.scalar(select(RoleCatalog).where(RoleCatalog.slug == payload.slug))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Track with slug '{payload.slug}' already exists",
        )

    track = RoleCatalog(
        slug=payload.slug,
        name=payload.name,
        description=payload.description,
        skill_focus_tags=payload.skill_focus_tags,
        question_mix_overrides=payload.question_mix_overrides,
        advanced_threshold_pct=payload.advanced_threshold_pct,
        is_active=payload.is_active,
    )
    session.add(track)
    await session.commit()
    await session.refresh(track)

    logger.info(
        "track_created",
        track_slug=track.slug,
        track_name=track.name,
        admin_user=user.user_id,
        is_active=track.is_active,
    )

    return TrackDetail(
        id=track.id,
        slug=track.slug,
        name=track.name,
        description=track.description,
        skill_focus_tags=track.skill_focus_tags,
        question_mix_overrides=track.question_mix_overrides,
        advanced_threshold_pct=track.advanced_threshold_pct,
        is_active=track.is_active,
        created_at=track.created_at,
        updated_at=track.updated_at,
    )


@router.get("/{slug}", response_model=TrackDetail)
async def get_track(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
) -> TrackDetail:
    """Get track details by slug."""
    track = await session.scalar(select(RoleCatalog).where(RoleCatalog.slug == slug))
    if not track:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Track '{slug}' not found",
        )

    return TrackDetail(
        id=track.id,
        slug=track.slug,
        name=track.name,
        description=track.description,
        skill_focus_tags=track.skill_focus_tags,
        question_mix_overrides=track.question_mix_overrides,
        advanced_threshold_pct=track.advanced_threshold_pct,
        is_active=track.is_active,
        created_at=track.created_at,
        updated_at=track.updated_at,
    )


@router.patch("/{slug}", response_model=TrackDetail)
async def update_track(
    slug: str,
    payload: TrackUpdate,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_roles(["admin"])),
) -> TrackDetail:
    """Update track (admin-only)."""
    track = await session.scalar(select(RoleCatalog).where(RoleCatalog.slug == slug))
    if not track:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Track '{slug}' not found",
        )

    # Update fields if provided
    if payload.name is not None:
        track.name = payload.name
    if payload.description is not None:
        track.description = payload.description
    if payload.skill_focus_tags is not None:
        track.skill_focus_tags = payload.skill_focus_tags
    if payload.question_mix_overrides is not None:
        track.question_mix_overrides = payload.question_mix_overrides
    if payload.advanced_threshold_pct is not None:
        track.advanced_threshold_pct = payload.advanced_threshold_pct
    if payload.is_active is not None:
        track.is_active = payload.is_active

    await session.commit()
    await session.refresh(track)

    updated_data = payload.model_dump(exclude_unset=True)
    logger.info(
        "track_updated",
        track_slug=track.slug,
        track_name=track.name,
        admin_user=user.user_id,
        updated_fields=[k for k, v in updated_data.items() if v is not None],
    )

    return TrackDetail(
        id=track.id,
        slug=track.slug,
        name=track.name,
        description=track.description,
        skill_focus_tags=track.skill_focus_tags,
        question_mix_overrides=track.question_mix_overrides,
        advanced_threshold_pct=track.advanced_threshold_pct,
        is_active=track.is_active,
        created_at=track.created_at,
        updated_at=track.updated_at,
    )


@router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_track(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_roles(["admin"])),
) -> None:
    """Soft delete track by marking as inactive (admin-only)."""
    track = await session.scalar(select(RoleCatalog).where(RoleCatalog.slug == slug))
    if not track:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Track '{slug}' not found",
        )

    track.is_active = False
    await session.commit()

    logger.info(
        "track_soft_deleted",
        track_slug=track.slug,
        track_name=track.name,
        admin_user=user.user_id,
    )
