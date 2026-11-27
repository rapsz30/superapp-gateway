"""Prodi dummy (terbuka) untuk registrasi publik dan panduan pribadi."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.config import get_settings
from src.domain.cakupan import penugasan_aktif
from src.models import Akun, Fakultas, Jurusan, Orang, Penugasan, Prodi


def cari_prodi_dari_jalur(db: Session, jalur: str) -> Prodi:
    bagian = [b.strip() for b in jalur.split("/")]
    if len(bagian) != 3 or not all(bagian):
        raise ValueError("Kolom prodi harus berbentuk KODE_FAKULTAS/KODE_JURUSAN/KODE_PRODI.")
    prodi = db.scalar(
        select(Prodi)
        .join(Jurusan, Jurusan.id == Prodi.jurusan_id)
        .join(Fakultas, Fakultas.id == Jurusan.fakultas_id)
        .where(Fakultas.kode == bagian[0], Jurusan.kode == bagian[1], Prodi.kode == bagian[2])
    )
    if prodi is None:
        raise ValueError(f"Prodi {jalur} tidak ditemukan.")
    if not prodi.aktif:
        raise ValueError(f"Prodi {jalur} tidak aktif.")
    return prodi


def jalur_prodi(db: Session, prodi: Prodi) -> str | None:
    jurusan = db.get(Jurusan, prodi.jurusan_id)
    if jurusan is None:
        return None
    fakultas = db.get(Fakultas, jurusan.fakultas_id)
    if fakultas is None:
        return None
    return f"{fakultas.kode}/{jurusan.kode}/{prodi.kode}"


def prodi_terbuka(db: Session) -> Prodi | None:
    jalur = get_settings().prodi_terbuka.strip()
    if not jalur:
        return None
    try:
        return cari_prodi_dari_jalur(db, jalur)
    except ValueError:
        return None


def adalah_prodi_terbuka(db: Session, prodi_id) -> bool:
    terbuka = prodi_terbuka(db)
    return terbuka is not None and terbuka.id == prodi_id


def dosen_terbuka(db: Session, prodi: Prodi, hari: date) -> Orang | None:
    """Kaprodi aktif prodi yang juga dosen PA aktif pada prodi itu dan punya akun aktif."""
    kaprodi = db.scalar(
        select(Orang)
        .join(Penugasan, Penugasan.orang_id == Orang.id)
        .where(
            Penugasan.peran == "kaprodi",
            Penugasan.unit_tipe == "prodi",
            Penugasan.unit_id == prodi.id,
            penugasan_aktif(hari),
        )
    )
    if kaprodi is None:
        return None
    pa = db.scalar(
        select(Penugasan.id).where(
            Penugasan.orang_id == kaprodi.id,
            Penugasan.peran == "dosen_pa",
            Penugasan.unit_tipe == "prodi",
            Penugasan.unit_id == prodi.id,
            penugasan_aktif(hari),
        )
    )
    if pa is None:
        return None
    akun = db.scalar(select(Akun).where(Akun.orang_id == kaprodi.id, Akun.status == "aktif"))
    if akun is None:
        return None
    return kaprodi


def registrasi_siap(db: Session, hari: date) -> tuple[Prodi, Orang] | None:
    """Kembalikan (prodi, dosen) bila sakelar aktif dan dosen siap; selain itu None."""
    s = get_settings()
    if not s.registrasi_aktif:
        return None
    prodi = prodi_terbuka(db)
    if prodi is None:
        return None
    dosen = dosen_terbuka(db, prodi, hari)
    if dosen is None:
        return None
    return prodi, dosen
