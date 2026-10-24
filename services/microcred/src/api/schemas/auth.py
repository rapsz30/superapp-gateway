"""Pydantic schemas for authentication endpoints."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field, StringConstraints


# Aturan panjang NIM. Format NIM UII belum dikonfirmasi, jadi batasnya sengaja longgar.
NIM_MIN_LENGTH = 6
NIM_MAX_LENGTH = 15

class UserRole(str, Enum):
    """User role enum."""

    STUDENT = "student"
    ADVISOR = "advisor"
    ADMIN = "admin"


# --- Request Schemas ---


class RegisterRequest(BaseModel):
    """Request schema for user registration."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password (min 8 characters)",
    )
    full_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=128)] = Field(
        ...,
        description="User's full name",
    )
    nim: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True,
            pattern=r"^[0-9]+$",
            min_length=NIM_MIN_LENGTH,
            max_length=NIM_MAX_LENGTH,
        ),
    ] = Field(..., description="Student ID number (digits only)")
    faculty: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=100)] = Field(
        ..., description="Faculty name"
    )
    study_program: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=100)] = Field(
        ..., description="Study program name"
    )
    role: UserRole = Field(
        default=UserRole.STUDENT,
        description="User role (defaults to student)",
    )


class LoginRequest(BaseModel):
    """Request schema for user login."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class RefreshTokenRequest(BaseModel):
    """Request schema for token refresh."""

    refresh_token: str = Field(..., description="Refresh token")


class ChangePasswordRequest(BaseModel):
    """Request schema for password change."""

    current_password: str = Field(..., description="Current password")
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="New password (min 8 characters)",
    )


# --- Response Schemas ---


class TokenResponse(BaseModel):
    """Response schema containing JWT tokens."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str | None = Field(None, description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token TTL in seconds")


class UserResponse(BaseModel):
    """Response schema for user data."""

    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    full_name: str | None = Field(None, description="User's full name")
    nim: str | None = Field(None, description="Student ID number")
    faculty: str | None = Field(None, description="Faculty name")
    study_program: str | None = Field(None, description="Study program name")
    role: str = Field(..., description="User role")
    status: str = Field(..., description="Account status")
    is_verified: bool = Field(..., description="Email verification status")
    created_at: datetime = Field(..., description="Account creation timestamp")
    last_login_at: datetime | None = Field(None, description="Last login timestamp")


class RegisterResponse(BaseModel):
    """Response schema for user registration."""

    message: str = Field(default="Registration successful")
    user: UserResponse
    tokens: TokenResponse


class LoginResponse(BaseModel):
    """Response schema for user login."""

    message: str = Field(default="Login successful")
    user: UserResponse
    tokens: TokenResponse


class MeResponse(BaseModel):
    """Response schema for current user info."""

    user: UserResponse
