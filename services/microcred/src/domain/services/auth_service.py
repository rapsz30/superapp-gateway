"""Authentication service with password hashing and user management."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import structlog
from passlib.context import CryptContext
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.auth import create_access_token
from src.core.config import get_settings
from src.infrastructure.db.models import UserModel, UserRole, UserStatus

logger = structlog.get_logger()

# Password hashing context with bcrypt (cost 12 as per security standards)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthError(Exception):
    """Base exception for authentication errors."""

    pass


class UserExistsError(AuthError):
    """Raised when attempting to register with existing email."""

    pass


class InvalidCredentialsError(AuthError):
    """Raised when login credentials are invalid."""

    pass


class UserNotFoundError(AuthError):
    """Raised when user is not found."""

    pass


class UserInactiveError(AuthError):
    """Raised when user account is inactive or suspended."""

    pass


class SelfRegistrationRoleNotAllowedError(AuthError):
    """Raised when user tries to self-register using a privileged role."""

    pass


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


class AuthService:
    """Service for authentication operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def register_user(
        self,
        *,
        email: str,
        password: str,
        full_name: str | None = None,
        role: str = "student",
    ) -> dict:
        """
        Register a new user.

        Returns:
            dict with user data and tokens
        """
        await logger.ainfo("register_attempt", email=email, role=role)

        # Validate role
        try:
            user_role = UserRole(role)
        except ValueError as exc:
            raise AuthError(f"Invalid role: {role}") from exc

        # Security policy: public self-registration cannot create admin users.
        if user_role == UserRole.ADMIN:
            raise SelfRegistrationRoleNotAllowedError("Self-registration as admin is not allowed")

        # Hash password
        hashed_password = hash_password(password)

        # Create user
        user = UserModel(
            email=email.lower(),
            hashed_password=hashed_password,
            full_name=full_name,
            role=user_role,
            status=UserStatus.ACTIVE,
            is_verified=False,
        )

        try:
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)
        except IntegrityError as exc:
            await self.session.rollback()
            await logger.awarning("register_duplicate_email", email=email)
            raise UserExistsError(f"User with email {email} already exists") from exc

        # Generate tokens
        tokens = self._generate_tokens(user)

        await logger.ainfo("register_success", user_id=user.id, email=email)

        return {
            "user": self._user_to_dict(user),
            "tokens": tokens,
        }

    async def login(self, *, email: str, password: str) -> dict:
        """
        Authenticate user with email and password.

        Returns:
            dict with user data and tokens
        """
        await logger.ainfo("login_attempt", email=email)

        # Find user
        stmt = select(UserModel).where(UserModel.email == email.lower())
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None:
            await logger.awarning("login_user_not_found", email=email)
            raise InvalidCredentialsError("Invalid email or password")

        # Check password
        if not verify_password(password, user.hashed_password):
            await logger.awarning("login_invalid_password", email=email)
            raise InvalidCredentialsError("Invalid email or password")

        # Check status
        if user.status != UserStatus.ACTIVE:
            await logger.awarning("login_inactive_user", email=email, status=user.status.value)
            raise UserInactiveError(f"Account is {user.status.value}")

        # Update last login
        await self.session.execute(
            update(UserModel).where(UserModel.id == user.id).values(last_login_at=datetime.now(UTC))
        )
        await self.session.commit()
        await self.session.refresh(user)

        # Generate tokens
        tokens = self._generate_tokens(user)

        await logger.ainfo("login_success", user_id=user.id, email=email)

        return {
            "user": self._user_to_dict(user),
            "tokens": tokens,
        }

    async def get_user_by_id(self, user_id: str) -> dict:
        """Get user by ID."""
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None:
            raise UserNotFoundError(f"User {user_id} not found")

        return self._user_to_dict(user)

    async def change_password(
        self, *, user_id: str, current_password: str, new_password: str
    ) -> dict:
        """Change user password."""
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None:
            raise UserNotFoundError(f"User {user_id} not found")

        if not verify_password(current_password, user.hashed_password):
            raise InvalidCredentialsError("Current password is incorrect")

        # Update password
        new_hashed = hash_password(new_password)
        await self.session.execute(
            update(UserModel).where(UserModel.id == user_id).values(hashed_password=new_hashed)
        )
        await self.session.commit()

        await logger.ainfo("password_changed", user_id=user_id)

        return {"message": "Password changed successfully"}

    def _generate_tokens(self, user: UserModel) -> dict:
        """Generate access and refresh tokens for user."""
        settings = get_settings()

        # Access token (shorter TTL)
        access_token = create_access_token(
            subject=user.id,
            roles=[user.role.value],
            email=user.email,
            expires_delta=timedelta(seconds=settings.access_token_ttl_seconds),
        )

        # Refresh token (longer TTL - 7 days)
        refresh_token = create_access_token(
            subject=user.id,
            roles=[user.role.value],
            email=user.email,
            expires_delta=timedelta(days=7),
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.access_token_ttl_seconds,
        }

    def _user_to_dict(self, user: UserModel) -> dict:
        """Convert UserModel to dict for response."""
        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.value,
            "status": user.status.value,
            "is_verified": user.is_verified,
            "created_at": user.created_at,
            "last_login_at": user.last_login_at,
        }
