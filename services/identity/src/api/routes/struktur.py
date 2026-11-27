"""Fakultas, jurusan, prodi. Baca untuk semua yang login; tulis hanya superadmin. Tanpa DELETE."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from src.api.deps import DB, Hal, Hari, Saya, Superadmin
from src.api.errors import galat, tidak_ditemukan
from src.api.schemas import (
    FakultasIn,
    FakultasOut,
    FakultasPatch,
    JurusanIn,
    JurusanOut,
    ProdiIn,
    ProdiOut,
    ProdiPatch,
)
from src.domain import audit
from src.domain.cakupan import penugasan_aktif
from src.domain.prodi_terbuka import adalah_prodi_terbuka
from src.models import Fakultas, Jurusan, KeanggotaanProdi, Penugasan, Prodi

router = APIRouter(tags=["struktur"])


def _prodi_out(db, obj: Prodi) -> ProdiOut:
    out = ProdiOut.model_validate(obj)
    out.terbuka = adalah_prodi_terbuka(db, obj.id)
    return out


def _ada_penugasan_aktif(db, unit_id: uuid.UUID, hari) -> bool:
    return (
        db.scalar(
            select(func.count()).select_from(Penugasan).where(
                Penugasan.unit_id == unit_id, penugasan_aktif(hari)
            )
        )
        or 0
    ) > 0


# ---------------- Fakultas ----------------
@router.get("/fakultas")
def daftar_fakultas(_: Saya, db: DB, hal: Hal, aktif: bool | None = None) -> dict:
    q = select(Fakultas)
    if aktif is not None:
        q = q.where(Fakultas.aktif == aktif)
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = db.scalars(q.order_by(Fakultas.kode).offset(hal.offset).limit(hal.ukuran)).all()
    return {"data": [FakultasOut.model_validate(r) for r in rows], "total": total}


@router.get("/fakultas/{fid}", response_model=FakultasOut)
def ambil_fakultas(fid: uuid.UUID, _: Saya, db: DB) -> Fakultas:
    obj = db.get(Fakultas, fid)
    if obj is None:
        raise tidak_ditemukan("Fakultas")
    return obj


@router.post("/fakultas", response_model=FakultasOut, status_code=201)
def buat_fakultas(body: FakultasIn, saya: Superadmin, db: DB) -> Fakultas:
    obj = Fakultas(kode=body.kode, nama=body.nama)
    db.add(obj)
    db.flush()
    audit.catat(db, saya.orang_id, "fakultas.buat", "fakultas", obj.id, None, audit.ke_dict(obj))
    db.commit()
    return obj


@router.patch("/fakultas/{fid}", response_model=FakultasOut)
def ubah_fakultas(fid: uuid.UUID, body: FakultasPatch, saya: Superadmin, db: DB, hari: Hari) -> Fakultas:
    obj = db.get(Fakultas, fid)
    if obj is None:
        raise tidak_ditemukan("Fakultas")
    sebelum = audit.ke_dict(obj)
    if body.nama is not None:
        obj.nama = body.nama
    if body.aktif is not None and body.aktif != obj.aktif:
        if not body.aktif:
            anak = db.scalar(
                select(func.count()).select_from(Jurusan).where(
                    Jurusan.fakultas_id == fid, Jurusan.aktif.is_(True)
                )
            )
            if anak:
                raise galat(409, f"Fakultas masih memiliki {anak} jurusan aktif.")
            if _ada_penugasan_aktif(db, fid, hari):
                raise galat(409, "Fakultas masih memiliki penugasan aktif (dekan atau lainnya).")
        obj.aktif = body.aktif
    audit.catat(db, saya.orang_id, "fakultas.ubah", "fakultas", obj.id, sebelum, audit.ke_dict(obj))
    db.commit()
    return obj


# ---------------- Jurusan ----------------
@router.get("/jurusan")
def daftar_jurusan(
    _: Saya, db: DB, hal: Hal, fakultas_id: uuid.UUID | None = None, aktif: bool | None = None
) -> dict:
    q = select(Jurusan)
    if fakultas_id:
        q = q.where(Jurusan.fakultas_id == fakultas_id)
    if aktif is not None:
        q = q.where(Jurusan.aktif == aktif)
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = db.scalars(q.order_by(Jurusan.kode).offset(hal.offset).limit(hal.ukuran)).all()
    return {"data": [JurusanOut.model_validate(r) for r in rows], "total": total}


@router.get("/jurusan/{jid}", response_model=JurusanOut)
def ambil_jurusan(jid: uuid.UUID, _: Saya, db: DB) -> Jurusan:
    obj = db.get(Jurusan, jid)
    if obj is None:
        raise tidak_ditemukan("Jurusan")
    return obj


@router.post("/jurusan", response_model=JurusanOut, status_code=201)
def buat_jurusan(body: JurusanIn, saya: Superadmin, db: DB) -> Jurusan:
    induk = db.get(Fakultas, body.fakultas_id)
    if induk is None:
        raise galat(400, "Fakultas tidak ditemukan.")
    if not induk.aktif:
        raise galat(409, "Fakultas tidak aktif.")
    obj = Jurusan(fakultas_id=body.fakultas_id, kode=body.kode, nama=body.nama)
    db.add(obj)
    db.flush()
    audit.catat(db, saya.orang_id, "jurusan.buat", "jurusan", obj.id, None, audit.ke_dict(obj))
    db.commit()
    return obj


@router.patch("/jurusan/{jid}", response_model=JurusanOut)
def ubah_jurusan(jid: uuid.UUID, body: FakultasPatch, saya: Superadmin, db: DB, hari: Hari) -> Jurusan:
    obj = db.get(Jurusan, jid)
    if obj is None:
        raise tidak_ditemukan("Jurusan")
    sebelum = audit.ke_dict(obj)
    if body.nama is not None:
        obj.nama = body.nama
    if body.aktif is not None and body.aktif != obj.aktif:
        if body.aktif:
            induk = db.get(Fakultas, obj.fakultas_id)
            if induk is None or not induk.aktif:
                raise galat(409, "Fakultas induk tidak aktif.")
        else:
            anak = db.scalar(
                select(func.count()).select_from(Prodi).where(
                    Prodi.jurusan_id == jid, Prodi.aktif.is_(True)
                )
            )
            if anak:
                raise galat(409, f"Jurusan masih memiliki {anak} prodi aktif.")
            if _ada_penugasan_aktif(db, jid, hari):
                raise galat(409, "Jurusan masih memiliki penugasan aktif (kajur atau dosen PA).")
        obj.aktif = body.aktif
    audit.catat(db, saya.orang_id, "jurusan.ubah", "jurusan", obj.id, sebelum, audit.ke_dict(obj))
    db.commit()
    return obj


# ---------------- Prodi ----------------
@router.get("/prodi")
def daftar_prodi(
    _: Saya, db: DB, hal: Hal, jurusan_id: uuid.UUID | None = None, aktif: bool | None = None
) -> dict:
    q = select(Prodi)
    if jurusan_id:
        q = q.where(Prodi.jurusan_id == jurusan_id)
    if aktif is not None:
        q = q.where(Prodi.aktif == aktif)
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = db.scalars(q.order_by(Prodi.kode).offset(hal.offset).limit(hal.ukuran)).all()
    return {"data": [_prodi_out(db, r) for r in rows], "total": total}


@router.get("/prodi/{pid}", response_model=ProdiOut)
def ambil_prodi(pid: uuid.UUID, _: Saya, db: DB) -> ProdiOut:
    obj = db.get(Prodi, pid)
    if obj is None:
        raise tidak_ditemukan("Prodi")
    return _prodi_out(db, obj)


@router.post("/prodi", response_model=ProdiOut, status_code=201)
def buat_prodi(body: ProdiIn, saya: Superadmin, db: DB) -> ProdiOut:
    induk = db.get(Jurusan, body.jurusan_id)
    if induk is None:
        raise galat(400, "Jurusan tidak ditemukan.")
    if not induk.aktif:
        raise galat(409, "Jurusan tidak aktif.")
    obj = Prodi(
        jurusan_id=body.jurusan_id,
        kode=body.kode,
        nama=body.nama,
        jenjang=body.jenjang,
        maks_sks_semester=body.maks_sks_semester,
    )
    db.add(obj)
    db.flush()
    audit.catat(db, saya.orang_id, "prodi.buat", "prodi", obj.id, None, audit.ke_dict(obj))
    db.commit()
    return _prodi_out(db, obj)


@router.patch("/prodi/{pid}", response_model=ProdiOut)
def ubah_prodi(pid: uuid.UUID, body: ProdiPatch, saya: Superadmin, db: DB, hari: Hari) -> ProdiOut:
    obj = db.get(Prodi, pid)
    if obj is None:
        raise tidak_ditemukan("Prodi")
    sebelum = audit.ke_dict(obj)
    if body.nama is not None:
        obj.nama = body.nama
    if body.jenjang is not None:
        obj.jenjang = body.jenjang
    if "maks_sks_semester" in body.model_fields_set:
        obj.maks_sks_semester = body.maks_sks_semester  # None mengembalikan ke bawaan layanan rekomendasi
    if body.aktif is not None and body.aktif != obj.aktif:
        if body.aktif:
            induk = db.get(Jurusan, obj.jurusan_id)
            if induk is None or not induk.aktif:
                raise galat(409, "Jurusan induk tidak aktif.")
        else:
            mhs = db.scalar(
                select(func.count()).select_from(KeanggotaanProdi).where(
                    KeanggotaanProdi.prodi_id == pid, KeanggotaanProdi.selesai.is_(None)
                )
            )
            if mhs:
                raise galat(409, f"Prodi masih memiliki {mhs} mahasiswa aktif.")
            if _ada_penugasan_aktif(db, pid, hari):
                raise galat(409, "Prodi masih memiliki penugasan aktif (kaprodi atau dosen PA).")
        obj.aktif = body.aktif
    audit.catat(db, saya.orang_id, "prodi.ubah", "prodi", obj.id, sebelum, audit.ke_dict(obj))
    db.commit()
    return _prodi_out(db, obj)


# ---------------- Pohon ----------------
@router.get("/struktur")
def pohon(_: Saya, db: DB, semua: bool = Query(False)) -> list[dict]:
    """Pohon fakultas, jurusan, prodi. Secara bawaan hanya unit aktif."""
    fak = db.scalars(select(Fakultas).order_by(Fakultas.kode)).all()
    jur = db.scalars(select(Jurusan).order_by(Jurusan.kode)).all()
    pro = db.scalars(select(Prodi).order_by(Prodi.kode)).all()

    def ok(o) -> bool:
        return semua or o.aktif

    prodi_per_jurusan: dict[uuid.UUID, list[dict]] = {}
    for p in pro:
        if ok(p):
            prodi_per_jurusan.setdefault(p.jurusan_id, []).append(
                {"id": str(p.id), "kode": p.kode, "nama": p.nama, "jenjang": p.jenjang, "aktif": p.aktif}
            )
    jurusan_per_fakultas: dict[uuid.UUID, list[dict]] = {}
    for j in jur:
        if ok(j):
            jurusan_per_fakultas.setdefault(j.fakultas_id, []).append(
                {
                    "id": str(j.id),
                    "kode": j.kode,
                    "nama": j.nama,
                    "aktif": j.aktif,
                    "prodi": prodi_per_jurusan.get(j.id, []),
                }
            )
    return [
        {
            "id": str(f.id),
            "kode": f.kode,
            "nama": f.nama,
            "aktif": f.aktif,
            "jurusan": jurusan_per_fakultas.get(f.id, []),
        }
        for f in fak
        if ok(f)
    ]
