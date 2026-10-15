from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Iterable, Sequence

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.auth import Role, TokenError, create_access_token, decode_access_token
from src.core.config import get_settings
from src.domain import User
from src.infrastructure.db.session import get_session

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),  # noqa: B008
) -> User:
    """Resolve the authenticated user from a bearer token."""
    if credentials is None:
        raise _unauthorized("Missing bearer token")

    try:
        payload = decode_access_token(credentials.credentials)
    except TokenError as exc:
        raise _unauthorized(str(exc)) from exc

    user_id = payload.get("sub")
    roles: Iterable[str] = payload.get("roles", [])

    if not user_id:
        raise _unauthorized("Token missing subject")

    if not roles:
        raise _forbidden("Token missing required roles")

    return User(user_id=user_id, email=payload.get("email", ""), roles=list(roles))


def require_roles(required_roles: Sequence[str]) -> Callable[[User], User]:
    """Dependency factory enforcing that the authenticated user has one of the required roles."""
    settings = get_settings()
    allowed = set(settings.allowed_roles)

    invalid_roles = [role for role in required_roles if role not in allowed]
    if invalid_roles:
        joined_roles = ", ".join(invalid_roles)
        raise ValueError(f"Unsupported role(s) requested: {joined_roles}")

    required = set(required_roles)

    def dependency(user: User = Depends(get_current_user)) -> User:  # noqa: B008
        if not required.intersection(user.roles):
            raise _forbidden("Insufficient role privileges")
        return user

    return dependency


def issue_smoke_token(user_id: str, *, role: Role, email: str | None = None) -> str:
    """Generate a signed token for manual smoke testing."""
    return create_access_token(user_id, roles=[role.value], email=email)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Provide an async SQLAlchemy session for API handlers."""
    async for session in get_session():
        yield session


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def _forbidden(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
