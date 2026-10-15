"""Authentication routes - register, login, token refresh, profile."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.deps import get_current_user, get_db_session
from src.api.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    MeResponse,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserResponse,
)
from src.domain import User
from src.domain.services.auth_service import (
    AuthService,
    InvalidCredentialsError,
    SelfRegistrationRoleNotAllowedError,
    UserExistsError,
    UserInactiveError,
    UserNotFoundError,
)

logger = structlog.get_logger()
router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
    description="Create a new user account with email, password, and optional name.",
)
async def register(
    payload: RegisterRequest,
    session: AsyncSession = Depends(get_db_session),
) -> RegisterResponse:
    """Register a new user."""
    service = AuthService(session)

    try:
        result = await service.register_user(
            email=payload.email,
            password=payload.password,
            full_name=payload.full_name,
            role=payload.role.value,
        )
    except UserExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except SelfRegistrationRoleNotAllowedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    return RegisterResponse(
        message="Registration successful",
        user=UserResponse(**result["user"]),
        tokens=TokenResponse(**result["tokens"]),
    )


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="User login",
    description="Authenticate user with email and password, returns JWT tokens.",
)
async def login(
    payload: LoginRequest,
    session: AsyncSession = Depends(get_db_session),
) -> LoginResponse:
    """Authenticate user and return tokens."""
    service = AuthService(session)

    try:
        result = await service.login(
            email=payload.email,
            password=payload.password,
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
    except UserInactiveError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    return LoginResponse(
        message="Login successful",
        user=UserResponse(**result["user"]),
        tokens=TokenResponse(**result["tokens"]),
    )


@router.get(
    "/me",
    response_model=MeResponse,
    summary="Get current user",
    description="Get the currently authenticated user's profile.",
)
async def get_me(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> MeResponse:
    """Get current authenticated user's profile."""
    service = AuthService(session)

    try:
        user_data = await service.get_user_by_id(user.user_id)
    except UserNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return MeResponse(user=UserResponse(**user_data))


@router.post(
    "/change-password",
    response_model=dict,
    summary="Change password",
    description="Change the current user's password.",
)
async def change_password(
    payload: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Change current user's password."""
    service = AuthService(session)

    try:
        result = await service.change_password(
            user_id=user.user_id,
            current_password=payload.current_password,
            new_password=payload.new_password,
        )
    except UserNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return result
