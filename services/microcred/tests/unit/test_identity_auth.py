from __future__ import annotations

import httpx
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from src.api import deps
from src.core.auth import create_access_token
from src.core.config import get_settings
from src.core.identity import IdentityError, fetch_identity_user


def _transport(status_code: int = 200, **overrides) -> httpx.MockTransport:
    body = {
        "akun_id": "akun-1",
        "email": "mhs@kampus.ac.id",
        "peran": ["mahasiswa"],
        "wajib_ganti_sandi": False,
        **overrides,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/auth/saya"
        assert request.headers["Authorization"] == "Bearer abc"
        return httpx.Response(status_code, json=body)

    return httpx.MockTransport(handler)


@pytest.mark.parametrize(
    ("campus_role", "role"),
    [("mahasiswa", "student"), ("dosen_pa", "advisor"), ("superadmin", "admin")],
)
async def test_campus_roles_are_mapped(campus_role: str, role: str) -> None:
    user = await fetch_identity_user(
        "http://identity", "abc", transport=_transport(peran=[campus_role])
    )

    assert user.user_id == "akun-1"
    assert user.email == "mhs@kampus.ac.id"
    assert user.roles == [role]


@pytest.mark.parametrize(
    ("transport", "status_code"),
    [
        (_transport(401), 401),
        (_transport(500), 503),
        (_transport(peran=["kaprodi"]), 403),
        (_transport(wajib_ganti_sandi=True), 403),
        (httpx.MockTransport(lambda request: httpx.Response(200, text="bukan json")), 503),
    ],
)
async def test_rejections(transport: httpx.MockTransport, status_code: int) -> None:
    with pytest.raises(IdentityError) as caught:
        await fetch_identity_user("http://identity", "abc", transport=transport)

    assert caught.value.status_code == status_code


async def test_unreachable_identity_fails_closed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("mati", request=request)

    with pytest.raises(IdentityError) as caught:
        await fetch_identity_user("http://identity", "abc", transport=httpx.MockTransport(handler))

    assert caught.value.status_code == 503


async def test_legacy_token_is_not_accepted_in_identity_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def reject(base_url: str, token: str):
        raise IdentityError("Invalid token", 401)

    monkeypatch.setattr(get_settings(), "identity_url", "http://identity")
    monkeypatch.setattr(deps, "fetch_identity_user", reject)
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials=create_access_token("lama", roles=["admin"])
    )

    with pytest.raises(HTTPException) as caught:
        await deps.get_current_user(credentials)

    assert caught.value.status_code == 401
