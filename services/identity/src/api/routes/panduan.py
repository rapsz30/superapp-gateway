"""Panduan akademik per prodi, berversi. Satu versi aktif per prodi."""

from __future__ import annotations

import uuid
from datetime import date
from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, select

from src.api.deps import DB, Saya
from src.api.errors import dilarang, galat, tidak_ditemukan
from src.api.schemas import PanduanOut
from src.core.config import get_settings
from src.domain import audit
from src.domain.pdf_teks import PdfTidakBisaDibaca, ekstrak_teks
from src.models import PanduanAkademik, Prodi

router = APIRouter(tags=["panduan"])


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


@router.get("/prodi/{pid}/panduan")
def daftar_versi(pid: uuid.UUID, _: Saya, db: DB) -> dict:
    _prodi_atau_404(db, pid)
    rows = db.scalars(
        select(PanduanAkademik).where(PanduanAkademik.prodi_id == pid).order_by(PanduanAkademik.versi.desc())
    ).all()
    return {"data": [PanduanOut.model_validate(r) for r in rows], "total": len(rows)}


@router.get("/prodi/{pid}/panduan/aktif", response_model=PanduanOut)
def panduan_aktif(pid: uuid.UUID, _: Saya, db: DB) -> PanduanAkademik:
    _prodi_atau_404(db, pid)
    obj = db.scalar(
        select(PanduanAkademik).where(PanduanAkademik.prodi_id == pid, PanduanAkademik.status == "aktif")
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
    if not prodi.aktif:
        raise galat(409, "Prodi tidak aktif.")
    isi = _baca_pdf(berkas)
    try:
        teks = ekstrak_teks(isi)
    except PdfTidakBisaDibaca as exc:
        raise galat(422, str(exc)) from None

    versi = (db.scalar(select(func.max(PanduanAkademik.versi)).where(PanduanAkademik.prodi_id == pid)) or 0) + 1
    folder = _akar() / str(pid)
    folder.mkdir(parents=True, exist_ok=True)
    jalur = folder / f"v{versi}.pdf"
    jalur.write_bytes(isi)
    try:
        obj = PanduanAkademik(
            prodi_id=pid,
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
        jalur.unlink(missing_ok=True)  # jangan tinggalkan berkas yatim
        raise
    return obj


@router.post("/panduan/{gid}/aktifkan", response_model=PanduanOut)
def aktifkan_panduan(gid: uuid.UUID, saya: Saya, db: DB) -> PanduanAkademik:
    obj = db.get(PanduanAkademik, gid)
    if obj is None:
        raise tidak_ditemukan("Panduan")
    if not saya.cakupan.kelola_prodi(obj.prodi_id):
        raise dilarang()
    # Kunci baris prodi supaya dua aktivasi bersamaan berjalan bergantian.
    db.execute(select(Prodi.id).where(Prodi.id == obj.prodi_id).with_for_update()).all()
    db.refresh(obj)
    if obj.status == "aktif":
        return obj
    lama = db.scalar(
        select(PanduanAkademik).where(
            PanduanAkademik.prodi_id == obj.prodi_id, PanduanAkademik.status == "aktif"
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


@router.get("/panduan/{gid}/berkas")
def unduh_berkas(gid: uuid.UUID, _: Saya, db: DB) -> FileResponse:
    obj = db.get(PanduanAkademik, gid)
    if obj is None:
        raise tidak_ditemukan("Panduan")
    jalur = (_akar() / obj.berkas_path).resolve()
    # Cegah path traversal bila nilai di database berubah.
    if _akar() not in jalur.parents or not jalur.is_file():
        raise tidak_ditemukan("Berkas")
    return FileResponse(jalur, media_type="application/pdf", filename=obj.berkas_nama)
