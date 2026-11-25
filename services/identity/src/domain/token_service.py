"""Penerbitan dan pencabutan token."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import update
from sqlalchemy.orm import Session

from src.api.errors import dilarang
from src.core.config import get_settings
from src.core.security import buat_access_token, buat_refresh_token
from src.domain.cakupan import hitung_cakupan
from src.models import Akun, RefreshToken


def terbitkan_token(db: Session, akun: Akun, hari: date) -> dict:
    """Buat pasangan access dan refresh token. Menolak akun yang belum punya peran aktif."""
    cak = hitung_cakupan(db, akun.orang_id, hari)
    if not cak.peran:
        raise dilarang("Akun belum memiliki peran aktif. Hubungi superadmin.")

    access, kedaluwarsa_detik = buat_access_token(
        akun_id=akun.id,
        orang_id=akun.orang_id,
        email=akun.email,
        peran=cak.peran,
        scopes=cak.scopes,
        versi_token=akun.versi_token,
        wajib_ganti_sandi=akun.wajib_ganti_sandi,
    )
    mentah, hashed = buat_refresh_token()
    db.add(
        RefreshToken(
            akun_id=akun.id,
            token_hash=hashed,
            kedaluwarsa=datetime.now(UTC) + timedelta(days=get_settings().refresh_token_hari),
        )
    )
    return {
        "access_token": access,
        "token_type": "bearer",
        "expires_in": kedaluwarsa_detik,
        "refresh_token": mentah,
        "wajib_ganti_sandi": akun.wajib_ganti_sandi,
        "peran": cak.peran,
    }


def cabut_semua_refresh(db: Session, akun_id) -> None:
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.akun_id == akun_id, RefreshToken.dicabut.is_(None))
        .values(dicabut=datetime.now(UTC))
    )
