"""Dependensi FastAPI: sesi database, pengguna saat ini, pembatas laju, paginasi."""

from __future__ import annotations

import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import date
from typing import Annotated

import jwt
from fastapi import Depends, Query, Request
from sqlalchemy.orm import Session

from src.api.errors import dilarang, galat
from src.core.config import get_settings
from src.core.security import baca_access_token
from src.core.waktu import hari_ini
from src.db import get_db
from src.domain.cakupan import Cakupan, hitung_cakupan
from src.models import Akun, Orang

DB = Annotated[Session, Depends(get_db)]


def hari() -> date:
    return hari_ini()


Hari = Annotated[date, Depends(hari)]


@dataclass
class Pengguna:
    akun: Akun
    orang: Orang
    cakupan: Cakupan

    @property
    def orang_id(self) -> uuid.UUID:
        return self.orang.id

    @property
    def superadmin(self) -> bool:
        return self.cakupan.superadmin


def _bearer(request: Request) -> str:
    header = request.headers.get("authorization", "")
    bagian = header.strip().split(None, 1)
    if len(bagian) != 2 or bagian[0].lower() != "bearer" or not bagian[1].strip():
        raise galat(401, "Token tidak ada atau tidak valid")
    return bagian[1].strip()


def _muat(request: Request, db: Session, hari_: date, boleh_wajib_ganti: bool) -> Pengguna:
    try:
        payload = baca_access_token(_bearer(request))
        akun_id = uuid.UUID(payload["sub"])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, ValueError, KeyError) as exc:
        pesan = "Token kedaluwarsa" if isinstance(exc, jwt.ExpiredSignatureError) else None
        raise galat(401, pesan or "Token tidak ada atau tidak valid") from None

    akun = db.get(Akun, akun_id)
    # versi_token membuat token lama langsung mati saat akun ditangguhkan atau sandi berubah.
    if akun is None or akun.status != "aktif" or akun.versi_token != payload.get("tv"):
        raise galat(401, "Token tidak ada atau tidak valid")
    if akun.wajib_ganti_sandi and not boleh_wajib_ganti:
        raise dilarang("Anda wajib mengganti sandi terlebih dahulu.")

    orang = db.get(Orang, akun.orang_id)
    assert orang is not None
    return Pengguna(akun=akun, orang=orang, cakupan=hitung_cakupan(db, orang.id, hari_))


def pengguna_saat_ini(request: Request, db: DB, hari_: Hari) -> Pengguna:
    return _muat(request, db, hari_, boleh_wajib_ganti=False)


def pengguna_boleh_ganti_sandi(request: Request, db: DB, hari_: Hari) -> Pengguna:
    """Dipakai ganti-sandi, saya, dan logout: tetap bisa diakses saat wajib ganti sandi."""
    return _muat(request, db, hari_, boleh_wajib_ganti=True)


Saya = Annotated[Pengguna, Depends(pengguna_saat_ini)]
SayaBebas = Annotated[Pengguna, Depends(pengguna_boleh_ganti_sandi)]


def hanya_superadmin(saya: Saya) -> Pengguna:
    if not saya.superadmin:
        raise dilarang()
    return saya


Superadmin = Annotated[Pengguna, Depends(hanya_superadmin)]


class Paginasi:
    def __init__(
        self,
        halaman: int = Query(1, ge=1),
        ukuran: int = Query(50, ge=1, le=200),
    ) -> None:
        self.halaman = halaman
        self.ukuran = ukuran

    @property
    def offset(self) -> int:
        return (self.halaman - 1) * self.ukuran


Hal = Annotated[Paginasi, Depends()]


# ---------- Pembatas laju login (dalam memori; cukup untuk satu instance) ----------
_gagal: dict[str, deque[float]] = defaultdict(deque)
_BATAS_KUNCI = 10_000


def _bersihkan(kunci: str, sekarang: float, jendela: int) -> deque[float]:
    antrean = _gagal[kunci]
    while antrean and sekarang - antrean[0] > jendela:
        antrean.popleft()
    return antrean


def terlalu_banyak_gagal(kunci: str) -> bool:
    s = get_settings()
    return len(_bersihkan(kunci, time.monotonic(), s.login_jendela_detik)) >= s.login_maks_gagal


def catat_gagal(kunci: str) -> None:
    s = get_settings()
    if len(_gagal) > _BATAS_KUNCI:
        _gagal.clear()  # lindungi memori dari banjir kunci acak
    sekarang = time.monotonic()
    _bersihkan(kunci, sekarang, s.login_jendela_detik).append(sekarang)


def reset_gagal(kunci: str) -> None:
    _gagal.pop(kunci, None)


def reset_semua_pembatas() -> None:
    _gagal.clear()


def alamat_klien(request: Request) -> str:
    return request.headers.get("x-real-ip") or (request.client.host if request.client else "?")
