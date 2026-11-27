"""Pemilihan panduan aktif: prodi biasa vs panduan pribadi pada prodi dummy."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.domain.prodi_terbuka import adalah_prodi_terbuka
from src.models import PanduanAkademik


def panduan_berlaku(
    db: Session, prodi_id: uuid.UUID, mahasiswa_id: uuid.UUID | None
) -> PanduanAkademik | None:
    """Panduan aktif yang berlaku untuk konteks mahasiswa / pengajuan.

    Prodi dummy: panduan aktif milik mahasiswa. Prodi lain: panduan aktif prodi (pemilik_id NULL).
    """
    if adalah_prodi_terbuka(db, prodi_id):
        if mahasiswa_id is None:
            return None
        return db.scalar(
            select(PanduanAkademik).where(
                PanduanAkademik.prodi_id == prodi_id,
                PanduanAkademik.pemilik_id == mahasiswa_id,
                PanduanAkademik.status == "aktif",
            )
        )
    return db.scalar(
        select(PanduanAkademik).where(
            PanduanAkademik.prodi_id == prodi_id,
            PanduanAkademik.pemilik_id.is_(None),
            PanduanAkademik.status == "aktif",
        )
    )


def pesan_tanpa_panduan(db: Session, prodi_id: uuid.UUID, nama_prodi: str) -> str:
    if adalah_prodi_terbuka(db, prodi_id):
        return "Anda belum mengunggah panduan akademik. Unggah panduan Anda terlebih dahulu."
    return f"Prodi {nama_prodi} belum memiliki panduan akademik aktif. Hubungi kaprodi."
