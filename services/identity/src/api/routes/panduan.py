"""Panduan akademik: versi prodi (kaprodi) dan versi pribadi (mahasiswa prodi dummy)."""

from __future__ import annotations

import uuid
from datetime import date
from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, select

from src.api.deps import DB, Hari, Saya
from src.api.errors import dilarang, galat, tidak_ditemukan
from src.api.schemas import PanduanOut
from src.core.config import get_settings
from src.domain import audit
from src.domain.pdf_teks import PdfTidakBisaDibaca, ekstrak_teks
from src.domain.prodi_terbuka import adalah_prodi_terbuka, prodi_terbuka
from src.models import Bimbingan, Orang, PanduanAkademik, Prodi

router = APIRouter(tags=["panduan"])

MAKS_VERSI_PRIBADI = 5


def _akar() -> Path:
    return Path(get_settings().panduan_dir).resolve()


def _baca_pdf(berkas: UploadFile) -> bytes:
    batas = get_settings().panduan_maks_mb * 1024 * 1024
    isi = berkas.file.read(batas + 1)
    if len(isi) > batas:
        raise galat(413, f"Berkas terlalu besar (maksimal {get_settings().panduan_maks_mb} MB).")
    if not isi.startswith(b"%PDF-"):
        raise galat(400, "Berkas harus berupa PDF.")
    return isi


def _prodi_atau_404(db, pid: uuid.UUID) -> Prodi:
    prodi = db.get(Prodi, pid)
    if prodi is None:
        raise tidak_ditemukan("Prodi")
    return prodi


def _boleh_unduh_pribadi(db, saya: Saya, obj: PanduanAkademik, hari: date) -> bool:
    if saya.superadmin or obj.pemilik_id == saya.orang_id:
        return True
    pa = db.scalar(
        select(Bimbingan.id).where(
            Bimbingan.mahasiswa_id == obj.pemilik_id,
            Bimbingan.dosen_id == saya.orang_id,
            Bimbingan.selesai.is_(None),
        )
    )
    return pa is not None


@router.get("/prodi/{pid}/panduan")
def daftar_versi(pid: uuid.UUID, _: Saya, db: DB) -> dict:
    _prodi_atau_404(db, pid)
    # Hanya panduan prodi (bukan pribadi).
    rows = db.scalars(
        select(PanduanAkademik)
        .where(PanduanAkademik.prodi_id == pid, PanduanAkademik.pemilik_id.is_(None))
        .order_by(PanduanAkademik.versi.desc())
    ).all()
    return {"data": [PanduanOut.model_validate(r) for r in rows], "total": len(rows)}


@router.get("/prodi/{pid}/panduan/aktif", response_model=PanduanOut)
def panduan_aktif(pid: uuid.UUID, _: Saya, db: DB) -> PanduanAkademik:
    _prodi_atau_404(db, pid)
    obj = db.scalar(
        select(PanduanAkademik).where(
            PanduanAkademik.prodi_id == pid,
            PanduanAkademik.pemilik_id.is_(None),
            PanduanAkademik.status == "aktif",
        )
    )
    if obj is None:
        raise tidak_ditemukan("Panduan aktif")
    return obj


@router.post("/prodi/{pid}/panduan", response_model=PanduanOut, status_code=201)
def unggah_panduan(
    pid: uuid.UUID,
    saya: Saya,
    db: DB,
    judul: str = Form(..., min_length=1, max_length=300),
    berlaku_mulai: date | None = Form(None),
    berkas: UploadFile = File(...),
) -> PanduanAkademik:
    """Unggah versi baru sebagai draf. Aktifkan lewat /panduan/{id}/aktifkan."""
    if not saya.cakupan.kelola_prodi(pid):
        raise dilarang()
    prodi = _prodi_atau_404(db, pid)
    if adalah_prodi_terbuka(db, pid):
        raise galat(409, "Prodi terbuka memakai panduan pribadi. Setiap mahasiswa mengunggah panduannya sendiri.")
    if not prodi.aktif:
        raise galat(409, "Prodi tidak aktif.")
    isi = _baca_pdf(berkas)
    try:
        teks = ekstrak_teks(isi)
    except PdfTidakBisaDibaca as exc:
        raise galat(422, str(exc)) from None

    versi = (
        db.scalar(
            select(func.max(PanduanAkademik.versi)).where(
                PanduanAkademik.prodi_id == pid, PanduanAkademik.pemilik_id.is_(None)
            )
        )
        or 0
    ) + 1
    folder = _akar() / str(pid)
    folder.mkdir(parents=True, exist_ok=True)
    jalur = folder / f"v{versi}.pdf"
    jalur.write_bytes(isi)
    try:
        obj = PanduanAkademik(
            prodi_id=pid,
            pemilik_id=None,
            versi=versi,
            judul=judul.strip(),
            berlaku_mulai=berlaku_mulai,
            status="draf",
            berkas_nama=(berkas.filename or f"panduan-v{versi}.pdf")[:255],
            berkas_path=str(jalur.relative_to(_akar())),
            teks=teks,
            teks_karakter=len(teks),
            dibuat_oleh=saya.orang_id,
        )
        db.add(obj)
        db.flush()
        audit.catat(db, saya.orang_id, "panduan.unggah", "panduan_akademik", obj.id, None, audit.ke_dict(obj))
        db.commit()
    except Exception:
        db.rollback()
        jalur.unlink(missing_ok=True)
        raise
    return obj


@router.post("/panduan/{gid}/aktifkan", response_model=PanduanOut)
def aktifkan_panduan(gid: uuid.UUID, saya: Saya, db: DB) -> PanduanAkademik:
    obj = db.get(PanduanAkademik, gid)
    if obj is None:
        raise tidak_ditemukan("Panduan")
    if obj.pemilik_id is not None:
        # Panduan pribadi diaktifkan otomatis saat unggah; jangan aktifkan milik orang lain.
        if obj.pemilik_id != saya.orang_id and not saya.superadmin:
            raise dilarang()
        raise galat(409, "Panduan pribadi diaktifkan otomatis saat diunggah.")
    if not saya.cakupan.kelola_prodi(obj.prodi_id):
        raise dilarang()
    db.execute(select(Prodi.id).where(Prodi.id == obj.prodi_id).with_for_update()).all()
    db.refresh(obj)
    if obj.status == "aktif":
        return obj
    lama = db.scalar(
        select(PanduanAkademik).where(
            PanduanAkademik.prodi_id == obj.prodi_id,
            PanduanAkademik.pemilik_id.is_(None),
            PanduanAkademik.status == "aktif",
        )
    )
    if lama is not None:
        sebelum = audit.ke_dict(lama)
        lama.status = "diarsipkan"
        audit.catat(db, saya.orang_id, "panduan.arsipkan", "panduan_akademik", lama.id, sebelum, audit.ke_dict(lama))
        db.flush()
    sebelum = audit.ke_dict(obj)
    obj.status = "aktif"
    audit.catat(db, saya.orang_id, "panduan.aktifkan", "panduan_akademik", obj.id, sebelum, audit.ke_dict(obj))
    db.commit()
    return obj


@router.get("/panduan/saya")
def daftar_panduan_saya(saya: Saya, db: DB) -> dict:
    rows = db.scalars(
        select(PanduanAkademik)
        .where(PanduanAkademik.pemilik_id == saya.orang_id)
        .order_by(PanduanAkademik.versi.desc())
    ).all()
    return {"data": [PanduanOut.model_validate(r) for r in rows], "total": len(rows)}


@router.post("/panduan/saya", response_model=PanduanOut, status_code=201)
def unggah_panduan_saya(
    saya: Saya,
    db: DB,
    hari: Hari,
    judul: str = Form("Panduan akademik saya", min_length=1, max_length=300),
    berlaku_mulai: date | None = Form(None),
    berkas: UploadFile = File(...),
) -> PanduanAkademik:
    cak = saya.cakupan
    if cak.prodi_mahasiswa is None or not adalah_prodi_terbuka(db, cak.prodi_mahasiswa):
        raise galat(409, "Unggah panduan pribadi hanya untuk mahasiswa prodi terbuka.")
    if prodi_terbuka(db) is None:
        raise galat(409, "Prodi terbuka tidak dikonfigurasi.")

    isi = _baca_pdf(berkas)
    try:
        teks = ekstrak_teks(isi)
    except PdfTidakBisaDibaca as exc:
        raise galat(422, str(exc)) from None

    # Kunci baris orang agar unggah bersamaan tidak bentrok nomor versi.
    db.execute(select(Orang.id).where(Orang.id == saya.orang_id).with_for_update()).all()

    jumlah = (
        db.scalar(
            select(func.count()).select_from(PanduanAkademik).where(
                PanduanAkademik.pemilik_id == saya.orang_id
            )
        )
        or 0
    )
    if jumlah >= MAKS_VERSI_PRIBADI:
        raise galat(409, f"Maksimal {MAKS_VERSI_PRIBADI} versi panduan. Hapus tidak didukung; hubungi admin bila perlu.")

    versi = (
        db.scalar(
            select(func.max(PanduanAkademik.versi)).where(PanduanAkademik.pemilik_id == saya.orang_id)
        )
        or 0
    ) + 1

    folder = _akar() / str(cak.prodi_mahasiswa) / str(saya.orang_id)
    folder.mkdir(parents=True, exist_ok=True)
    jalur = folder / f"v{versi}.pdf"
    jalur.write_bytes(isi)
    try:
        lama = db.scalar(
            select(PanduanAkademik).where(
                PanduanAkademik.pemilik_id == saya.orang_id, PanduanAkademik.status == "aktif"
            )
        )
        if lama is not None:
            sebelum = audit.ke_dict(lama)
            lama.status = "diarsipkan"
            audit.catat(
                db, saya.orang_id, "panduan.arsipkan", "panduan_akademik", lama.id, sebelum, audit.ke_dict(lama)
            )
            db.flush()

        obj = PanduanAkademik(
            prodi_id=cak.prodi_mahasiswa,
            pemilik_id=saya.orang_id,
            versi=versi,
            judul=judul.strip(),
            berlaku_mulai=berlaku_mulai or hari,
            status="aktif",
            berkas_nama=(berkas.filename or f"panduan-saya-v{versi}.pdf")[:255],
            berkas_path=str(jalur.relative_to(_akar())),
            teks=teks,
            teks_karakter=len(teks),
            dibuat_oleh=saya.orang_id,
        )
        db.add(obj)
        db.flush()
        audit.catat(db, saya.orang_id, "panduan.unggah_pribadi", "panduan_akademik", obj.id, None, audit.ke_dict(obj))
        db.commit()
    except Exception:
        db.rollback()
        jalur.unlink(missing_ok=True)
        raise
    return obj


@router.get("/panduan/{gid}/berkas")
def unduh_berkas(gid: uuid.UUID, saya: Saya, db: DB, hari: Hari) -> FileResponse:
    obj = db.get(PanduanAkademik, gid)
    if obj is None:
        raise tidak_ditemukan("Panduan")
    if obj.pemilik_id is not None and not _boleh_unduh_pribadi(db, saya, obj, hari):
        raise tidak_ditemukan("Panduan")
    jalur = (_akar() / obj.berkas_path).resolve()
    if _akar() not in jalur.parents or not jalur.is_file():
        raise tidak_ditemukan("Berkas")
    return FileResponse(jalur, media_type="application/pdf", filename=obj.berkas_nama)
