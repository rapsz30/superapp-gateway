from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class TrackItem(BaseModel):
    slug: str
    name: str
    description: str | None = None
    question_count: int


class TracksResponse(BaseModel):
    tracks: list[TrackItem]


class TrackDetail(BaseModel):
    id: int
    slug: str
    name: str
    description: str | None = None
    skill_focus_tags: list[str] | None = None
    question_mix_overrides: dict[str, int] | None = None
    advanced_threshold_pct: float
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TrackCreate(BaseModel):
    slug: str = Field(..., min_length=1, max_length=64, pattern=r"^[a-z0-9-]+$")
    name: str = Field(..., min_length=1, max_length=128)
    description: str | None = None
    skill_focus_tags: list[str] | None = None
    question_mix_overrides: dict[str, int] | None = None
    advanced_threshold_pct: float = Field(default=70.0, ge=0.0, le=100.0)
    is_active: bool = True


class TrackUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=128)
    description: str | None = None
    skill_focus_tags: list[str] | None = None
    question_mix_overrides: dict[str, int] | None = None
    advanced_threshold_pct: float | None = Field(default=None, ge=0.0, le=100.0)
    is_active: bool | None = None
