from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import UTC, datetime, timedelta
from enum import Enum

import jwt
from src.core.config import get_settings


class TokenError(Exception):
    """Raised when a token cannot be decoded or validated."""


class Role(str, Enum):
    STUDENT = "student"
    ADVISOR = "advisor"
    ADMIN = "admin"

    @classmethod
    def contains(cls, value: str) -> bool:
        return value in {role.value for role in cls}


def create_access_token(
    subject: str,
    *,
    roles: Sequence[str],
    email: str | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Generate a signed JWT access token."""
    settings = get_settings()

    invalid_roles = [role for role in roles if role not in settings.allowed_roles]
    if invalid_roles:
        joined_roles = ", ".join(invalid_roles)
        raise TokenError(f"Unsupported role(s): {joined_roles}")

    now = datetime.now(UTC)
    ttl = expires_delta or timedelta(seconds=settings.access_token_ttl_seconds)
    payload = {
        "sub": subject,
        "roles": list(roles),
        "iat": int(now.timestamp()),
        "exp": int((now + ttl).timestamp()),
        "iss": settings.app_name,
    }

    if email:
        payload["email"] = email

    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token."""
    settings = get_settings()

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "roles", "exp"]},
        )
    except jwt.PyJWTError as exc:  # pragma: no cover - third-party raises numerous subclasses
        raise TokenError("Invalid token") from exc

    _ensure_roles(payload.get("roles", []))
    return payload


def _ensure_roles(roles: Iterable[str]) -> None:
    for role in roles:
        if not Role.contains(role):
            raise TokenError(f"Unsupported role: {role}")
