"""Orang, akun, dan impor CSV. Tulis hanya superadmin."""

from __future__ import annotations

import csv
import io
import uuid

from fastapi import APIRouter, File, Query, UploadFile
from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from src.api.deps import DB, Hal, Hari, Saya, Superadmin
from src.api.errors import PESAN_BATASAN, galat, tidak_ditemukan
from src.api.schemas import (
    AkunIn,
    AkunOut,
    AkunRingkas,
    AkunStatusIn,
    OrangIn,
    OrangOut,
    OrangPatch,
)
from src.core.security import hash_sandi, sandi_acak, validasi_kebijakan_sandi
from src.domain import audit
from src.domain.cakupan import orang_terlihat, penugasan_aktif
from src.domain.prodi_terbuka import cari_prodi_dari_jalur
from src.domain.token_service import cabut_semua_refresh
from src.models import Akun, Fakultas, Jurusan, KeanggotaanProdi, Orang, Penugasan, Prodi

router = APIRouter(tags=["orang"])

IMPOR_MAKS_BARIS = 2000
IMPOR_MAKS_BYTE = 2 * 1024 * 1024
_email_adapter = TypeAdapter(EmailStr)


def _peran_orang(db, orang_id: uuid.UUID, hari) -> list[str]:
    peran = set(
        db.scalars(
            select(Penugasan.peran).where(Penugasan.orang_id == orang_id, penugasan_aktif(hari))
        )
    )
    ada_anggota = db.scalar(
        select(func.count()).select_from(KeanggotaanProdi).where(
            KeanggotaanProdi.orang_id == orang_id, KeanggotaanProdi.selesai.is_(None)
        )
    )
    if ada_anggota:
        peran.add("mahasiswa")
    urutan = ["superadmin", "dekan", "kajur", "kaprodi", "dosen_pa", "mahasiswa"]
    return [r for r in urutan if r in peran]


def _keluaran(db, orang: Orang, hari, tampilkan_akun: bool) -> OrangOut:
    akun = None
    if tampilkan_akun:
        a = db.scalar(select(Akun).where(Akun.orang_id == orang.id))
        if a:
            akun = AkunRingkas(
                id=a.id, email=a.email, status=a.status, wajib_ganti_sandi=a.wajib_ganti_sandi
            )
    return OrangOut(
        id=orang.id,
        nama_lengkap=orang.nama_lengkap,
        nim=orang.nim,
        nidn=orang.nidn,
        email_kontak=orang.email_kontak,
        prodi_isian=orang.prodi_isian if tampilkan_akun else None,
        pt_isian=orang.pt_isian if tampilkan_akun else None,
        peran=_peran_orang(db, orang.id, hari),
        akun=akun,
    )


@router.get("/orang")
def daftar_orang(
    saya: Saya,
    db: DB,
    hal: Hal,
    hari: Hari,
    q: str | None = Query(None, max_length=100),
    prodi_id: uuid.UUID | None = None,
    peran: str | None = Query(None, pattern="^(superadmin|dekan|kajur|kaprodi|dosen_pa|mahasiswa)$"),
) -> dict:
    stmt = select(Orang)
    terlihat = orang_terlihat(db, saya.cakupan, hari)
    if terlihat is not None:
        stmt = stmt.where(Orang.id.in_(select(terlihat.c[0])))
    if q:
        pola = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(Orang.nama_lengkap.ilike(pola), Orang.nim.ilike(pola), Orang.nidn.ilike(pola))
        )
    if prodi_id:
        stmt = stmt.where(
            Orang.id.in_(
                select(KeanggotaanProdi.orang_id).where(
                    KeanggotaanProdi.prodi_id == prodi_id, KeanggotaanProdi.selesai.is_(None)
                )
            )
        )
    if peran == "mahasiswa":
        stmt = stmt.where(
            Orang.id.in_(select(KeanggotaanProdi.orang_id).where(KeanggotaanProdi.selesai.is_(None)))
        )
    elif peran:
        stmt = stmt.where(
            Orang.id.in_(
                select(Penugasan.orang_id).where(Penugasan.peran == peran, penugasan_aktif(hari))
            )
        )
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(Orang.nama_lengkap).offset(hal.offset).limit(hal.ukuran)).all()
    return {"data": [_keluaran(db, o, hari, saya.superadmin) for o in rows], "total": total}


# Rute tetap harus didaftarkan sebelum /orang/{oid}.
@router.post("/orang/impor")
def impor_orang(saya: Superadmin, db: DB, hari: Hari, berkas: UploadFile = File(...)) -> dict:
    """Impor CSV. Kolom: nama_lengkap (wajib), nim, nidn, email_kontak, email_akun,
    prodi (FAKULTAS/JURUSAN/PRODI memakai kode), angkatan.

    Setiap baris diproses sendiri-sendiri: baris yang gagal tidak menggagalkan yang lain.
    Sandi sementara hanya muncul sekali di laporan ini.
    """
    mentah = berkas.file.read(IMPOR_MAKS_BYTE + 1)
    if len(mentah) > IMPOR_MAKS_BYTE:
        raise galat(413, "Berkas terlalu besar (maksimal 2 MB).")
    try:
        teks = mentah.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise galat(400, "Berkas harus berenkode UTF-8.") from None

    pembaca = csv.DictReader(io.StringIO(teks))
    if not pembaca.fieldnames or "nama_lengkap" not in [f.strip() for f in pembaca.fieldnames]:
        raise galat(400, "Kolom nama_lengkap wajib ada pada baris pertama.")
    baris = list(pembaca)
    if len(baris) > IMPOR_MAKS_BARIS:
        raise galat(400, f"Terlalu banyak baris (maksimal {IMPOR_MAKS_BARIS}).")

    laporan: list[dict] = []
    for nomor, row in enumerate(baris, start=2):  # baris 1 = header
        r = {(k or "").strip(): (v or "").strip() for k, v in row.items()}
        item: dict = {"baris": nomor}
        try:
            with db.begin_nested():
                if not r.get("nama_lengkap"):
                    raise ValueError("nama_lengkap kosong.")
                email_kontak = r.get("email_kontak") or None
                if email_kontak:
                    _email_adapter.validate_python(email_kontak)
                orang = Orang(
                    nama_lengkap=r["nama_lengkap"][:200],
                    nim=r.get("nim") or None,
                    nidn=r.get("nidn") or None,
                    email_kontak=email_kontak,
                )
                db.add(orang)
                db.flush()
                audit.catat(db, saya.orang_id, "orang.buat", "orang", orang.id, None, audit.ke_dict(orang))

                if r.get("email_akun"):
                    email = str(_email_adapter.validate_python(r["email_akun"])).lower()
                    sandi = sandi_acak()
                    akun = Akun(orang_id=orang.id, email=email, sandi_hash=hash_sandi(sandi))
                    db.add(akun)
                    db.flush()
                    audit.catat(db, saya.orang_id, "akun.buat", "akun", akun.id, None, audit.ke_dict(akun))
                    item["email"] = email
                    item["sandi_sementara"] = sandi

                if r.get("prodi"):
                    prodi = cari_prodi_dari_jalur(db, r["prodi"])
                    angkatan = None
                    if r.get("angkatan"):
                        angkatan = int(r["angkatan"])
                        if not 1990 <= angkatan <= 2100:
                            raise ValueError("angkatan di luar rentang.")
                    anggota = KeanggotaanProdi(
                        orang_id=orang.id, prodi_id=prodi.id, angkatan=angkatan, status="aktif", mulai=hari
                    )
                    db.add(anggota)
                    db.flush()
                    audit.catat(
                        db, saya.orang_id, "keanggotaan.buat", "keanggotaan_prodi", anggota.id,
                        None, audit.ke_dict(anggota),
                    )
                item.update(status="ok", orang_id=str(orang.id))
        except IntegrityError as exc:
            nama = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
            item.pop("sandi_sementara", None)
            item.update(status="gagal", alasan=PESAN_BATASAN.get(nama or "", "Data melanggar aturan."))
        except (ValueError, ValidationError) as exc:
            item.pop("sandi_sementara", None)
            item.update(status="gagal", alasan=_pesan(exc))
        laporan.append(item)

    db.commit()
    berhasil = sum(1 for x in laporan if x["status"] == "ok")
    return {"total": len(laporan), "berhasil": berhasil, "gagal": len(laporan) - berhasil, "baris": laporan}


def _pesan(exc: Exception) -> str:
    if isinstance(exc, ValidationError):
        return "Format email tidak valid."
    return str(exc)


@router.get("/orang/{oid}", response_model=OrangOut)
def ambil_orang(oid: uuid.UUID, saya: Saya, db: DB, hari: Hari) -> OrangOut:
    obj = db.get(Orang, oid)
    terlihat = orang_terlihat(db, saya.cakupan, hari)
    if obj is None or (
        terlihat is not None
        and db.scalar(select(func.count()).select_from(terlihat).where(terlihat.c[0] == oid)) == 0
    ):
        raise tidak_ditemukan("Orang")
    # Isian registrasi hanya untuk superadmin atau orang itu sendiri.
    return _keluaran(db, obj, hari, saya.superadmin or oid == saya.orang_id)


@router.post("/orang", response_model=OrangOut, status_code=201)
def buat_orang(body: OrangIn, saya: Superadmin, db: DB, hari: Hari) -> OrangOut:
    obj = Orang(**body.model_dump())
    db.add(obj)
    db.flush()
    audit.catat(db, saya.orang_id, "orang.buat", "orang", obj.id, None, audit.ke_dict(obj))
    db.commit()
    return _keluaran(db, obj, hari, True)


@router.patch("/orang/{oid}", response_model=OrangOut)
def ubah_orang(oid: uuid.UUID, body: OrangPatch, saya: Superadmin, db: DB, hari: Hari) -> OrangOut:
    obj = db.get(Orang, oid)
    if obj is None:
        raise tidak_ditemukan("Orang")
    sebelum = audit.ke_dict(obj)
    for kolom, nilai in body.model_dump(exclude_unset=True).items():
        setattr(obj, kolom, nilai)
    audit.catat(db, saya.orang_id, "orang.ubah", "orang", obj.id, sebelum, audit.ke_dict(obj))
    db.commit()
    return _keluaran(db, obj, hari, True)


# ---------------- Akun ----------------
def _jumlah_superadmin_lain(db, orang_id: uuid.UUID, hari) -> int:
    """Superadmin aktif (penugasan aktif dan akun aktif) selain orang ini."""
    return (
        db.scalar(
            select(func.count(func.distinct(Penugasan.orang_id)))
            .select_from(Penugasan)
            .join(Akun, Akun.orang_id == Penugasan.orang_id)
            .where(
                Penugasan.peran == "superadmin",
                penugasan_aktif(hari),
                Akun.status == "aktif",
                Penugasan.orang_id != orang_id,
            )
        )
        or 0
    )


@router.post("/akun", response_model=AkunOut, status_code=201)
def buat_akun(body: AkunIn, saya: Superadmin, db: DB) -> AkunOut:
    orang = db.get(Orang, body.orang_id)
    if orang is None:
        raise galat(400, "Orang tidak ditemukan.")
    sandi = body.sandi
    dibuat_otomatis = sandi is None
    if sandi is None:
        sandi = sandi_acak()
    else:
        pesan = validasi_kebijakan_sandi(sandi, body.email)
        if pesan:
            raise galat(400, pesan)
    akun = Akun(orang_id=orang.id, email=body.email, sandi_hash=hash_sandi(sandi), wajib_ganti_sandi=True)
    db.add(akun)
    db.flush()
    audit.catat(db, saya.orang_id, "akun.buat", "akun", akun.id, None, audit.ke_dict(akun))
    db.commit()
    return AkunOut(
        id=akun.id,
        orang_id=akun.orang_id,
        email=akun.email,
        status=akun.status,
        wajib_ganti_sandi=akun.wajib_ganti_sandi,
        sandi_sementara=sandi if dibuat_otomatis else None,
    )


@router.post("/akun/{aid}/atur-ulang-sandi", response_model=AkunOut)
def atur_ulang_sandi(aid: uuid.UUID, saya: Superadmin, db: DB) -> AkunOut:
    akun = db.get(Akun, aid)
    if akun is None:
        raise tidak_ditemukan("Akun")
    sandi = sandi_acak()
    akun.sandi_hash = hash_sandi(sandi)
    akun.wajib_ganti_sandi = True
    akun.versi_token += 1
    cabut_semua_refresh(db, akun.id)
    audit.catat(db, saya.orang_id, "akun.atur_ulang_sandi", "akun", akun.id)
    db.commit()
    return AkunOut(
        id=akun.id,
        orang_id=akun.orang_id,
        email=akun.email,
        status=akun.status,
        wajib_ganti_sandi=True,
        sandi_sementara=sandi,
    )


@router.patch("/akun/{aid}/status", response_model=AkunOut)
def ubah_status_akun(aid: uuid.UUID, body: AkunStatusIn, saya: Superadmin, db: DB, hari: Hari) -> AkunOut:
    akun = db.get(Akun, aid)
    if akun is None:
        raise tidak_ditemukan("Akun")
    if body.status != "aktif" and akun.status == "aktif":
        adalah_superadmin = db.scalar(
            select(func.count()).select_from(Penugasan).where(
                Penugasan.orang_id == akun.orang_id,
                Penugasan.peran == "superadmin",
                penugasan_aktif(hari),
            )
        )
        if adalah_superadmin and _jumlah_superadmin_lain(db, akun.orang_id, hari) == 0:
            raise galat(409, "Tidak boleh menonaktifkan superadmin aktif terakhir.")
    sebelum = {"status": akun.status}
    if body.status != akun.status:
        akun.status = body.status
        if body.status != "aktif":
            akun.versi_token += 1
            cabut_semua_refresh(db, akun.id)
    audit.catat(db, saya.orang_id, "akun.ubah_status", "akun", akun.id, sebelum, {"status": akun.status})
    db.commit()
    return AkunOut(
        id=akun.id,
        orang_id=akun.orang_id,
        email=akun.email,
        status=akun.status,
        wajib_ganti_sandi=akun.wajib_ganti_sandi,
    )
