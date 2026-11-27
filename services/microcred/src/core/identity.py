"""Autentikasi akun kampus lewat layanan identity."""

from __future__ import annotations

import httpx
from src.core.auth import Role
from src.domain import User

# Peran identity -> peran Micro-cred. Peran lain (dekan, kajur, kaprodi) tidak punya padanan.
ROLE_MAP = {
    "mahasiswa": Role.STUDENT,
    "dosen_pa": Role.ADVISOR,
    "superadmin": Role.ADMIN,
}
TIMEOUT_SECONDS = 5.0


class IdentityError(Exception):
    """Raised when the identity service cannot authenticate the caller."""

    def __init__(self, detail: str, status_code: int) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


async def fetch_identity_user(
    base_url: str,
    token: str,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
) -> User:
    """Ask identity who owns the token.

    Identity memeriksa tanda tangan, masa berlaku, versi token, dan status akun, sehingga
    Micro-cred tidak perlu memegang JWT_SECRET milik identity.
    """
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS, transport=transport) as client:
            response = await client.get(
                f"{base_url.rstrip('/')}/auth/saya",
                headers={"Authorization": f"Bearer {token}"},
            )
    except httpx.HTTPError as exc:
        raise IdentityError("Identity service unavailable", 503) from exc

    if response.status_code == 401:
        raise IdentityError("Invalid token", 401)
    if response.status_code != 200:
        raise IdentityError("Identity service unavailable", 503)

    try:
        body = response.json()
        user_id = str(body["akun_id"])
        campus_roles = list(body["peran"])
        must_change_password = bool(body["wajib_ganti_sandi"])
        email = str(body.get("email") or "")
    except (ValueError, KeyError, TypeError) as exc:
        raise IdentityError("Identity service unavailable", 503) from exc

    if must_change_password:
        raise IdentityError("Password change required", 403)

    roles = [ROLE_MAP[role].value for role in campus_roles if role in ROLE_MAP]
    if not roles:
        raise IdentityError("Insufficient role privileges", 403)

    return User(user_id=user_id, email=email, roles=roles)
