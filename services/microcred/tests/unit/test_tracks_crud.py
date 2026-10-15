from __future__ import annotations

import pytest
from fastapi import status
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_list_tracks_returns_active_only(async_client: AsyncClient) -> None:
    """GET /tracks should return only active tracks."""
    response = await async_client.get("/tracks")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "tracks" in data
    assert isinstance(data["tracks"], list)


async def test_create_track_requires_admin(async_client: AsyncClient, admin_token: str) -> None:
    """POST /tracks should require admin role."""
    # Try without auth - should fail
    response = await async_client.post(
        "/tracks",
        json={
            "slug": "test-engineer",
            "name": "Test Engineer",
            "description": "Testing professional",
            "skill_focus_tags": ["testing", "automation"],
            "is_active": True,
        },
    )
    assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    # Try with admin auth - should succeed
    response = await async_client.post(
        "/tracks",
        json={
            "slug": "test-engineer",
            "name": "Test Engineer",
            "description": "Testing professional",
            "skill_focus_tags": ["testing", "automation"],
            "question_mix_overrides": {"theoretical": 3, "essay": 5, "profile": 2},
            "is_active": True,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["slug"] == "test-engineer"
    assert data["name"] == "Test Engineer"
    assert data["skill_focus_tags"] == ["testing", "automation"]
    assert data["advanced_threshold_pct"] == 70.0
    assert "created_at" in data
    assert "updated_at" in data


async def test_create_track_duplicate_slug_fails(
    async_client: AsyncClient, admin_token: str
) -> None:
    """Creating track with duplicate slug should fail."""
    # Create first track
    await async_client.post(
        "/tracks",
        json={
            "slug": "duplicate-test",
            "name": "First",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Try to create with same slug
    response = await async_client.post(
        "/tracks",
        json={
            "slug": "duplicate-test",
            "name": "Second",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == status.HTTP_409_CONFLICT


async def test_get_track_by_slug(async_client: AsyncClient, admin_token: str) -> None:
    """GET /tracks/{slug} should return track details."""
    # Create track first
    await async_client.post(
        "/tracks",
        json={
            "slug": "get-test",
            "name": "Get Test",
            "skill_focus_tags": ["skill1", "skill2"],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Get track
    response = await async_client.get("/tracks/get-test")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["slug"] == "get-test"
    assert data["name"] == "Get Test"
    assert data["skill_focus_tags"] == ["skill1", "skill2"]
    assert data["advanced_threshold_pct"] == 70.0


async def test_get_nonexistent_track_returns_404(async_client: AsyncClient) -> None:
    """GET /tracks/{slug} for nonexistent track should return 404."""
    response = await async_client.get("/tracks/nonexistent")
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_update_track_requires_admin(async_client: AsyncClient, admin_token: str) -> None:
    """PATCH /tracks/{slug} should require admin role."""
    # Create track
    await async_client.post(
        "/tracks",
        json={"slug": "update-test", "name": "Original Name"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Try update without auth
    response = await async_client.patch(
        "/tracks/update-test",
        json={"name": "New Name"},
    )
    assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    # Update with admin auth
    response = await async_client.patch(
        "/tracks/update-test",
        json={
            "name": "New Name",
            "skill_focus_tags": ["new", "tags"],
            "advanced_threshold_pct": 75.0,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "New Name"
    assert data["skill_focus_tags"] == ["new", "tags"]
    assert data["advanced_threshold_pct"] == 75.0


async def test_delete_track_soft_deletes(async_client: AsyncClient, admin_token: str) -> None:
    """DELETE /tracks/{slug} should soft delete by setting is_active=False."""
    # Create track
    await async_client.post(
        "/tracks",
        json={"slug": "delete-test", "name": "Delete Test"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Delete track
    response = await async_client.delete(
        "/tracks/delete-test",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verify it's soft deleted (not in active list)
    response = await async_client.get("/tracks")
    tracks = response.json()["tracks"]
    assert not any(t["slug"] == "delete-test" for t in tracks)

    # But still accessible via direct get (for audit trail)
    response = await async_client.get("/tracks/delete-test")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["is_active"] is False


async def test_update_nonexistent_track_returns_404(
    async_client: AsyncClient, admin_token: str
) -> None:
    """PATCH /tracks/{slug} for nonexistent track should return 404."""
    response = await async_client.patch(
        "/tracks/nonexistent",
        json={"name": "New Name"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
