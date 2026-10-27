"""Unit tests for authentication service."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from src.api.schemas.auth import LoginRequest, RegisterRequest, UserResponse
from src.domain.services.auth_service import (
    AuthService,
    UserExistsError,
    hash_password,
    verify_password,
)


# Data identitas mahasiswa yang wajib pada RegisterRequest
IDENTITY = {
    "full_name": "Test User",
    "nim": "12345678",
    "faculty": "Fakultas Teknologi Industri",
    "study_program": "Informatika",
}


class TestPasswordHashing:
    """Tests for password hashing functions."""

    def test_hash_password_returns_bcrypt_hash(self) -> None:
        """Hash should start with bcrypt prefix."""
        password = "test_password_123"
        hashed = hash_password(password)

        # bcrypt hashes start with $2b$
        assert hashed.startswith("$2b$")
        assert len(hashed) == 60  # bcrypt hash length

    def test_hash_password_is_not_plaintext(self) -> None:
        """Hash should not contain plaintext password."""
        password = "test_password_123"
        hashed = hash_password(password)

        assert password not in hashed

    def test_hash_password_unique_per_call(self) -> None:
        """Same password should produce different hashes (due to salt)."""
        password = "test_password_123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        assert hash1 != hash2

    def test_verify_password_correct(self) -> None:
        """Verify should return True for correct password."""
        password = "test_password_123"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self) -> None:
        """Verify should return False for incorrect password."""
        password = "test_password_123"
        wrong_password = "wrong_password"
        hashed = hash_password(password)

        assert verify_password(wrong_password, hashed) is False

    def test_verify_password_case_sensitive(self) -> None:
        """Passwords should be case-sensitive."""
        password = "TestPassword123"
        hashed = hash_password(password)

        assert verify_password("testpassword123", hashed) is False
        assert verify_password("TESTPASSWORD123", hashed) is False


class TestAuthSchemas:
    """Tests for auth request/response schemas."""

    def test_register_request_valid(self) -> None:
        """Valid registration request should pass validation."""
        request = RegisterRequest(
            email="test@example.com",
            password="password123",
            full_name="Test User",
            nim="12345678",
            faculty="Fakultas Teknologi Industri",
            study_program="Informatika",
        )

        assert request.nim == "12345678"
        assert request.email == "test@example.com"
        assert request.password == "password123"
        assert request.full_name == "Test User"
        assert request.role.value == "student"  # default

    def test_register_request_password_min_length(self) -> None:
        """Password must be at least 8 characters."""
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(
                email="test@example.com",
                password="short",
                **IDENTITY,
            )

        assert "String should have at least 8 characters" in str(exc_info.value)

    def test_register_request_invalid_email(self) -> None:
        """Invalid email should fail validation."""
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(
                email="not-an-email",
                password="password123",
                **IDENTITY,
            )

        assert "value is not a valid email address" in str(exc_info.value)

    def test_register_request_nim_letters_rejected(self) -> None:
        """NIM berisi huruf harus ditolak."""
        with pytest.raises(ValidationError):
            RegisterRequest(email="test@example.com", password="password123", **{**IDENTITY, "nim": "abc12345"})

    def test_register_request_nim_length_bounds(self) -> None:
        """NIM di luar batas panjang harus ditolak."""
        for nim in ("12345", "1" * 16):
            with pytest.raises(ValidationError):
                RegisterRequest(email="test@example.com", password="password123", **{**IDENTITY, "nim": nim})

    def test_register_request_missing_identity_rejected(self) -> None:
        """Field identitas yang hilang harus ditolak."""
        for missing in IDENTITY:
            data = {k: v for k, v in IDENTITY.items() if k != missing}
            with pytest.raises(ValidationError):
                RegisterRequest(email="test@example.com", password="password123", **data)

    def test_register_request_strips_whitespace(self) -> None:
        """Spasi di awal dan akhir harus di-strip."""
        request = RegisterRequest(
            email="test@example.com",
            password="password123",
            full_name="  Test User ",
            nim=" 12345678 ",
            faculty=" Fakultas ",
            study_program=" Informatika ",
        )

        assert request.full_name == "Test User"
        assert request.nim == "12345678"
        assert request.faculty == "Fakultas"
        assert request.study_program == "Informatika"

    def test_login_request_valid(self) -> None:
        """Valid login request should pass validation."""
        request = LoginRequest(
            email="test@example.com",
            password="password123",
        )

        assert request.email == "test@example.com"
        assert request.password == "password123"

    def test_user_response_serialization(self) -> None:
        """UserResponse should serialize correctly."""
        from datetime import datetime

        response = UserResponse(
            id="user-123",
            email="test@example.com",
            full_name="Test User",
            role="student",
            status="active",
            is_verified=False,
            created_at=datetime(2024, 12, 30, 10, 0, 0),
            last_login_at=None,
        )

        assert response.id == "user-123"
        assert response.email == "test@example.com"
        assert response.role == "student"

class _DriverError(Exception):
    """Tiruan error driver database dengan atribut constraint_name."""

    def __init__(self, message: str, constraint_name: str | None = None) -> None:
        super().__init__(message)
        if constraint_name is not None:
            self.constraint_name = constraint_name


class TestRegisterDuplicateDetection:
    """Pelanggaran unik dibedakan lewat nama constraint, bukan substring."""

    @staticmethod
    def _service_failing_with(orig: Exception) -> AuthService:
        session = MagicMock()
        no_row = MagicMock()
        no_row.first.return_value = None
        session.execute = AsyncMock(return_value=no_row)  # pra-cek email/NIM: belum ada
        session.add = MagicMock()
        session.commit = AsyncMock(side_effect=IntegrityError("INSERT", {}, orig))
        session.rollback = AsyncMock()
        return AuthService(session)

    @pytest.mark.asyncio
    async def test_email_constraint_with_nim_like_email_reports_email(self) -> None:
        orig = _DriverError(
            'duplicate key value violates unique constraint "users_email_key" '
            "Key (email)=(nimas@example.com) already exists.",
            constraint_name="users_email_key",
        )
        service = self._service_failing_with(orig)

        with pytest.raises(UserExistsError) as exc_info:
            await service.register_user(
                email="nimas@example.com",
                password="password123",
                full_name="Nimas",
                nim="12345678",
                faculty="Fakultas",
                study_program="Informatika",
            )

        assert "email" in str(exc_info.value)
        assert "NIM" not in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_email_violation_without_constraint_name_reports_email(self) -> None:
        orig = _DriverError(
            'duplicate key value violates unique constraint "users_email_key" '
            "Key (email)=(nimas@example.com) already exists."
        )
        service = self._service_failing_with(orig)

        with pytest.raises(UserExistsError) as exc_info:
            await service.register_user(
                email="nimas@example.com",
                password="password123",
                full_name="Nimas",
                nim="12345678",
                faculty="Fakultas",
                study_program="Informatika",
            )

        assert "email" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_nim_constraint_reports_nim(self) -> None:
        orig = _DriverError(
            'duplicate key value violates unique constraint "ix_users_nim"',
            constraint_name="ix_users_nim",
        )
        service = self._service_failing_with(orig)

        with pytest.raises(UserExistsError) as exc_info:
            await service.register_user(
                email="orang@example.com",
                password="password123",
                full_name="Orang",
                nim="12345678",
                faculty="Fakultas",
                study_program="Informatika",
            )

        assert "NIM" in str(exc_info.value)
