"""Pencatatan audit. Hanya-tambah; database menolak ubah dan hapus."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session

from src.models import AuditLog

# Kolom yang tidak boleh masuk jejak audit.
RAHASIA = frozenset({"sandi_hash", "token_hash", "teks"})  # teks panduan terlalu besar untuk audit


def ke_dict(obj: Any, kecuali: tuple[str, ...] = ()) -> dict[str, Any]:
    hasil: dict[str, Any] = {}
    for kolom in obj.__table__.columns:
        if kolom.name in RAHASIA or kolom.name in kecuali:
            continue
        nilai = getattr(obj, kolom.name)
        if isinstance(nilai, uuid.UUID | date | datetime):
            nilai = str(nilai) if not isinstance(nilai, datetime) else nilai.isoformat()
        hasil[kolom.name] = nilai
    return hasil


def catat(
    db: Session,
    pelaku_id: uuid.UUID | None,
    aksi: str,
    objek_tipe: str,
    objek_id: uuid.UUID | None,
    sebelum: dict[str, Any] | None = None,
    sesudah: dict[str, Any] | None = None,
) -> None:
    db.add(
        AuditLog(
            pelaku_id=pelaku_id,
            aksi=aksi,
            objek_tipe=objek_tipe,
            objek_id=objek_id,
            sebelum=sebelum,
            sesudah=sesudah,
        )
    )
