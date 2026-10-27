"""Verifier JWT untuk NGINX auth_request.

NGINX memanggil GET /verify untuk setiap request terproteksi. Respons 200 berarti
lolos, 401 berarti token bermasalah, 403 berarti role tidak diizinkan.
Token tidak pernah dicatat di log.
"""

from __future__ import annotations

import json
import os
import re

import jwt
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# ---------------------------------------------------------------------------
# Kebijakan role: daftar aturan sederhana.
# Method di bawah pada path yang cocok hanya boleh untuk role admin.
# ---------------------------------------------------------------------------
WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
ADMIN_ONLY_RULES = [
    (WRITE_METHODS, re.compile(r"^/api/micro-cred/(tracks|questions)(/.*)?$")),
]
ADMIN_ROLE = "admin"

# Nama env sama dengan services/microcred/src/core/config.py (JWT_SECRET sengaja tanpa default)
# Nilai bawaan JWT_SECRET di services/microcred/src/core/config.py. Tidak boleh dipakai.
INSECURE_DEFAULT_SECRET = "replace-with-secure-secret"
JWT_SECRET = os.environ.get("JWT_SECRET", "")
if not JWT_SECRET.strip() or JWT_SECRET == INSECURE_DEFAULT_SECRET:
    # Pesan sengaja tidak memuat nilai secret
    raise RuntimeError(
        "JWT_SECRET tidak diatur, kosong, atau masih memakai nilai bawaan Micro-cred. "
        "Isi JWT_SECRET dengan secret sungguhan di .env Micro-cred. Verifier tidak mau start."
    )
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
DEFAULT_ROLES = ("student", "advisor", "admin")


def _load_allowed_roles() -> frozenset[str]:
    """ALLOWED_ROLES dibaca seperti pydantic-settings (JSON), dengan cadangan pemisah koma."""
    raw = os.environ.get("ALLOWED_ROLES")
    if not raw:
        return frozenset(DEFAULT_ROLES)
    try:
        value = json.loads(raw)
        if isinstance(value, list):
            return frozenset(str(v) for v in value)
    except ValueError:
        pass
    return frozenset(part.strip() for part in raw.split(",") if part.strip())


ALLOWED_ROLES = _load_allowed_roles()

app = FastAPI(title="auth-verifier", docs_url=None, redoc_url=None, openapi_url=None)


def _deny(status_code: int, detail: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": detail})


def _bearer_token(header: str | None) -> str | None:
    """Ambil token dari 'Authorization: Bearer <token>' (skema tidak peka huruf besar kecil)."""
    if not header:
        return None
    parts = header.strip().split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        return None
    return parts[1].strip()


def _latin1_ok(value: str) -> bool:
    """True bila nilai aman dikirim sebagai header HTTP (latin-1, tanpa CR/LF)."""
    if "\r" in value or "\n" in value:
        return False
    try:
        value.encode("latin-1")
    except UnicodeEncodeError:
        return False
    return True


def _clean_path(uri: str) -> str:
    """Buang query string dan rapikan slash ganda. Path sudah dinormalisasi oleh NGINX."""
    return re.sub(r"/+", "/", uri.split("?", 1)[0])


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/verify")
def verify(request: Request) -> JSONResponse:
    token = _bearer_token(request.headers.get("authorization"))
    if token is None:
        return _deny(401, "Token tidak ada atau tidak valid")

    try:
        # Algoritma dikunci ke satu nilai. Token dengan algoritma lain atau "none" ditolak.
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "roles", "exp"]},
        )
    except jwt.ExpiredSignatureError:
        return _deny(401, "Token kedaluwarsa")
    except jwt.PyJWTError:
        return _deny(401, "Token tidak ada atau tidak valid")

    # sub wajib string non-kosong (dan bisa dikirim sebagai header)
    sub = payload.get("sub")
    if not isinstance(sub, str) or not sub.strip() or not _latin1_ok(sub):
        return _deny(401, "Token tidak ada atau tidak valid")

    roles = payload.get("roles")
    if (
        not isinstance(roles, list)
        or not roles
        or not all(isinstance(r, str) and r in ALLOWED_ROLES for r in roles)
    ):
        return _deny(403, "Akses ditolak")

    method = request.headers.get("x-original-method")
    uri = request.headers.get("x-original-uri")
    if not method or uri is None:
        # Fail closed: verifier hanya valid bila dipanggil lewat NGINX
        return _deny(403, "Akses ditolak")

    path = _clean_path(uri)
    for methods, pattern in ADMIN_ONLY_RULES:
        if method.upper() in methods and pattern.match(path) and ADMIN_ROLE not in roles:
            return _deny(403, "Akses ditolak")

    response = JSONResponse(status_code=200, content={"status": "ok"})
    email = str(payload.get("email") or "")
    if not _latin1_ok(email):
        # Header HTTP hanya latin-1: email non-ASCII dikirim kosong agar tidak crash
        email = ""
    response.headers["X-User-Id"] = sub
    response.headers["X-User-Roles"] = ",".join(roles)
    response.headers["X-User-Email"] = email
    return response

