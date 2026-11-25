"""Hash sandi, token akses (JWT), dan token penyegar (opaque)."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from src.core.config import get_settings

MAKS_BYTE_SANDI = 72  # batas bcrypt
MIN_PANJANG_SANDI = 10

# Hash tetap untuk menyamakan waktu respons saat akun tidak ditemukan.
_HASH_PALSU = bcrypt.hashpw(b"tidak-dipakai", bcrypt.gensalt(rounds=12))


def validasi_kebijakan_sandi(sandi: str, email: str | None = None) -> str | None:
    """Kembalikan pesan galat, atau None bila sandi memenuhi kebijakan."""
    if len(sandi) < MIN_PANJANG_SANDI:
        return f"Sandi minimal {MIN_PANJANG_SANDI} karakter."
    if len(sandi.encode("utf-8")) > MAKS_BYTE_SANDI:
        return f"Sandi terlalu panjang (maksimal {MAKS_BYTE_SANDI} byte)."
    if email and sandi.lower() == email.lower():
        return "Sandi tidak boleh sama dengan email."
    return None


def hash_sandi(sandi: str) -> str:
    rounds = max(4, get_settings().bcrypt_rounds)
    return bcrypt.hashpw(sandi.encode("utf-8"), bcrypt.gensalt(rounds=rounds)).decode("ascii")


def cek_sandi(sandi: str, hash_tersimpan: str | None) -> bool:
    """Selalu menjalankan satu perbandingan bcrypt, juga bila akun tidak ada."""
    if len(sandi.encode("utf-8")) > MAKS_BYTE_SANDI:
        bcrypt.checkpw(b"x", _HASH_PALSU)
        return False
    target = hash_tersimpan.encode("ascii") if hash_tersimpan else _HASH_PALSU
    ok = bcrypt.checkpw(sandi.encode("utf-8"), target)
    return ok and hash_tersimpan is not None


def sandi_acak(panjang: int = 14) -> str:
    return secrets.token_urlsafe(panjang)[:panjang]


def buat_access_token(
    *,
    akun_id: uuid.UUID,
    orang_id: uuid.UUID,
    email: str,
    peran: list[str],
    scopes: list[dict[str, Any]],
    versi_token: int,
    wajib_ganti_sandi: bool,
) -> tuple[str, int]:
    s = get_settings()
    sekarang = datetime.now(UTC)
    exp = sekarang + timedelta(minutes=s.access_token_menit)
    payload = {
        "sub": str(akun_id),
        "orang": str(orang_id),
        "email": email,
        "roles": peran,
        "scopes": scopes,
        "tv": versi_token,
        "gs": wajib_ganti_sandi,
        "iat": sekarang,
        "exp": exp,
        "iss": s.jwt_issuer,
    }
    token = jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm)
    return token, s.access_token_menit * 60


def baca_access_token(token: str) -> dict[str, Any]:
    """Lempar jwt.PyJWTError bila tidak sah. Algoritma dikunci ke satu nilai."""
    s = get_settings()
    return jwt.decode(
        token,
        s.jwt_secret,
        algorithms=[s.jwt_algorithm],
        issuer=s.jwt_issuer,
        options={"require": ["sub", "roles", "exp", "tv"]},
    )


def buat_refresh_token() -> tuple[str, str]:
    """Kembalikan (token mentah untuk klien, hash untuk database)."""
    mentah = secrets.token_urlsafe(48)
    return mentah, hash_refresh(mentah)


def hash_refresh(mentah: str) -> str:
    return hashlib.sha256(mentah.encode("utf-8")).hexdigest()
