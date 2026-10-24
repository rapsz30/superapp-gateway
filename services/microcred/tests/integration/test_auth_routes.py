"""Integration tests for authentication endpoints."""

from __future__ import annotations

import pytest
from fastapi import status
from httpx import AsyncClient


# Data identitas mahasiswa yang kini wajib saat registrasi
IDENTITY = {
    "full_name": "Test User",
    "nim": "12345678",
    "faculty": "Fakultas Teknologi Industri",
    "study_program": "Informatika",
}


@pytest.fixture
def test_user() -> dict:
    """Test user data."""
    return {
        "email": "testuser@example.com",
        "password": "testpassword123",
        **IDENTITY,
    }


class TestRegisterEndpoint:
    """Tests for POST /auth/register endpoint."""

    @pytest.mark.asyncio
    async def test_register_success(self, async_client: AsyncClient, test_user: dict) -> None:
        """Successful registration should return 201 with user and tokens."""
        response = await async_client.post("/auth/register", json=test_user)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        assert data["message"] == "Registration successful"
        assert data["user"]["email"] == test_user["email"]
        assert data["user"]["full_name"] == test_user["full_name"]
        assert data["user"]["nim"] == test_user["nim"]
        assert data["user"]["faculty"] == test_user["faculty"]
        assert data["user"]["study_program"] == test_user["study_program"]
        assert data["user"]["role"] == "student"
        assert data["user"]["status"] == "active"
        assert "access_token" in data["tokens"]
        assert "refresh_token" in data["tokens"]
        assert data["tokens"]["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_register_duplicate_email(
        self, async_client: AsyncClient, test_user: dict
    ) -> None:
        """Registering with existing email should return 409."""
        # First registration
        await async_client.post("/auth/register", json=test_user)

        # Duplicate registration
        response = await async_client.post("/auth/register", json=test_user)

        assert response.status_code == status.HTTP_409_CONFLICT
        assert "already exists" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_register_duplicate_nim(self, async_client: AsyncClient, test_user: dict) -> None:
        """NIM yang sudah terdaftar (email berbeda) harus ditolak 409."""
        await async_client.post("/auth/register", json=test_user)

        response = await async_client.post(
            "/auth/register", json={**test_user, "email": "other@example.com"}
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        assert "NIM" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_register_nim_with_letters_rejected(
        self, async_client: AsyncClient, test_user: dict
    ) -> None:
        """NIM berisi huruf harus 422."""
        response = await async_client.post(
            "/auth/register", json={**test_user, "nim": "abc12345"}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    @pytest.mark.parametrize("missing", ["full_name", "nim", "faculty", "study_program"])
    async def test_register_missing_identity_field_rejected(
        self, async_client: AsyncClient, test_user: dict, missing: str
    ) -> None:
        """Field identitas yang hilang harus 422."""
        payload = {k: v for k, v in test_user.items() if k != missing}

        response = await async_client.post("/auth/register", json=payload)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_register_strips_whitespace(
        self, async_client: AsyncClient, test_user: dict
    ) -> None:
        """Spasi di awal dan akhir field identitas harus di-strip."""
        payload = {
            **test_user,
            "full_name": "  Test User  ",
            "nim": "  12345678  ",
            "faculty": " Fakultas Teknologi Industri ",
            "study_program": " Informatika ",
        }

        response = await async_client.post("/auth/register", json=payload)

        assert response.status_code == status.HTTP_201_CREATED
        user = response.json()["user"]
        assert user["full_name"] == "Test User"
        assert user["nim"] == "12345678"
        assert user["faculty"] == "Fakultas Teknologi Industri"
        assert user["study_program"] == "Informatika"

    @pytest.mark.asyncio
    async def test_me_includes_identity_fields(
        self, async_client: AsyncClient, test_user: dict
    ) -> None:
        """GET /auth/me harus memuat nim, faculty, dan study_program."""
        register = await async_client.post("/auth/register", json=test_user)
        token = register.json()["tokens"]["access_token"]

        response = await async_client.get(
            "/auth/me", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        user = response.json()["user"]
        assert user["nim"] == test_user["nim"]
        assert user["faculty"] == test_user["faculty"]
        assert user["study_program"] == test_user["study_program"]

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, async_client: AsyncClient) -> None:
        """Invalid email format should return 422."""
        response = await async_client.post(
            "/auth/register",
            json={
                "email": "not-an-email",
                "password": "password123",
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_register_short_password(self, async_client: AsyncClient) -> None:
        """Password under 8 chars should return 422."""
        response = await async_client.post(
            "/auth/register",
            json={
                "email": "test@example.com",
                "password": "short",
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_register_with_advisor_role(self, async_client: AsyncClient) -> None:
        """Registration with advisor role should work."""
        response = await async_client.post(
            "/auth/register",
            json={
                "email": "advisor@example.com",
                "password": "password123",
                **IDENTITY,
                "role": "advisor",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["user"]["role"] == "advisor"

    @pytest.mark.asyncio
    async def test_register_with_admin_role_forbidden(self, async_client: AsyncClient) -> None:
        """Self-registration with admin role should be forbidden."""
        response = await async_client.post(
            "/auth/register",
            json={
                "email": "admin-self-register@example.com",
                "password": "password123",
                **IDENTITY,
                "role": "admin",
            },
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "not allowed" in response.json()["detail"].lower()


class TestLoginEndpoint:
    """Tests for POST /auth/login endpoint."""

    @pytest.mark.asyncio
    async def test_login_success(self, async_client: AsyncClient, test_user: dict) -> None:
        """Successful login should return tokens."""
        # Register first
        await async_client.post("/auth/register", json=test_user)

        # Login
        response = await async_client.post(
            "/auth/login",
            json={
                "email": test_user["email"],
                "password": test_user["password"],
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["message"] == "Login successful"
        assert data["user"]["email"] == test_user["email"]
        assert "access_token" in data["tokens"]
        assert "refresh_token" in data["tokens"]

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, async_client: AsyncClient, test_user: dict) -> None:
        """Wrong password should return 401."""
        # Register first
        await async_client.post("/auth/register", json=test_user)

        # Login with wrong password
        response = await async_client.post(
            "/auth/login",
            json={
                "email": test_user["email"],
                "password": "wrongpassword",
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid email or password" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, async_client: AsyncClient) -> None:
        """Login with non-existent email should return 401."""
        response = await async_client.post(
            "/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "password123",
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestMeEndpoint:
    """Tests for GET /auth/me endpoint."""

    @pytest.mark.asyncio
    async def test_me_success(self, async_client: AsyncClient, test_user: dict) -> None:
        """Authenticated user should get their profile."""
        # Register and get token
        register_response = await async_client.post("/auth/register", json=test_user)
        token = register_response.json()["tokens"]["access_token"]

        # Get profile
        response = await async_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["user"]["email"] == test_user["email"]
        assert data["user"]["full_name"] == test_user["full_name"]

    @pytest.mark.asyncio
    async def test_me_no_token(self, async_client: AsyncClient) -> None:
        """Request without token should return 401."""
        response = await async_client.get("/auth/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestChangePasswordEndpoint:
    """Tests for POST /auth/change-password endpoint."""

    @pytest.mark.asyncio
    async def test_change_password_success(
        self, async_client: AsyncClient, test_user: dict
    ) -> None:
        """Changing password should succeed with correct current password."""
        # Register and get token
        register_response = await async_client.post("/auth/register", json=test_user)
        token = register_response.json()["tokens"]["access_token"]

        # Change password
        response = await async_client.post(
            "/auth/change-password",
            json={
                "current_password": test_user["password"],
                "new_password": "newpassword123",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == "Password changed successfully"

        # Verify login with new password works
        login_response = await async_client.post(
            "/auth/login",
            json={
                "email": test_user["email"],
                "password": "newpassword123",
            },
        )
        assert login_response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(
        self, async_client: AsyncClient, test_user: dict
    ) -> None:
        """Wrong current password should return 400."""
        # Register and get token
        register_response = await async_client.post("/auth/register", json=test_user)
        token = register_response.json()["tokens"]["access_token"]

        # Try to change with wrong current password
        response = await async_client.post(
            "/auth/change-password",
            json={
                "current_password": "wrongpassword",
                "new_password": "newpassword123",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Current password is incorrect" in response.json()["detail"]
