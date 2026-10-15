from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class RoleCatalog:
    """Represents a role available within the credentialing platform."""

    name: str
    description: str | None = None


@dataclass(slots=True)
class User:
    """Represents an authenticated actor within the system."""

    user_id: str
    email: str = ""
    roles: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(slots=True)
class Assessment:
    """Placeholder for the assessment domain aggregate."""

    assessment_id: str
    owner_id: str
    status: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
