from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Request, Response
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from src.api.deps import (
    DB,
    Hari,
    SayaBebas,
    alamat_klien,
    catat_gagal,
    catat_registrasi,
    reset_gagal,
    terlalu_banyak_gagal,
    terlalu_banyak_registrasi,
)
from src.api.errors import galat
from src.api.schemas import (
    GantiSandiIn,
    LoginIn,
    LogoutIn,
    RefreshIn,
    RegisterIn,
    RegistrasiStatusOut,
    TokenOut,
)
from src.core.config import get_settings
from src.core.security import cek_sandi, hash_refresh, hash_sandi, validasi_kebijakan_sandi
from src.domain import audit
from src.domain.cakupan import penugasan_aktif
from src.domain.mahasiswa_baru import buat_mahasiswa
from src.domain.prodi_terbuka import adalah_prodi_terbuka, dosen_terbuka, prodi_terbuka
from src.domain.token_service import cabut_semua_refresh, terbitkan_token
from src.models import (
    Akun,
    Bimbingan,
    Fakultas,
    Jurusan,
    KeanggotaanProdi,
    Orang,
    Penugasan,
    Prodi,
    RefreshToken,
)

router = APIRouter(prefix="/auth", tags=["auth"])

GALAT_LOGIN = "Email atau sandi salah"
_LOKAL_CADANGAN = frozenset({"admin", "superadmin"})
_LOKAL_MAHASISWA = re.compile(r"^mahasiswa\d+$")


def _email_cadangan(email: str) -> bool:
    lokal = email.split("@", 1)[0].lower()
    return lokal in _LOKAL_CADANGAN or bool(_LOKAL_MAHASISWA.fullmatch(lokal))


def _registrasi_aktif(db) -> bool:
    s = get_settings()
    return bool(s.registrasi_aktif and prodi_terbuka(db) is not None)


@router.get("/registrasi", response_model=RegistrasiStatusOut)
def status_registrasi(db: DB) -> RegistrasiStatusOut:
    return RegistrasiStatusOut(aktif=_registrasi_aktif(db))


@router.post("/register", response_model=TokenOut, status_code=201)
def register(body: RegisterIn, db: DB, hari: Hari) -> dict:
    if not get_settings().registrasi_aktif or prodi_terbuka(db) is None:
        raise galat(404, "Registrasi tidak tersedia.")
    if terlalu_banyak_registrasi():
        raise galat(429, "Batas pendaftaran tercapai. Coba lagi nanti.")

    prodi = prodi_terbuka(db)
    assert prodi is not None
    dosen = dosen_terbuka(db, prodi, hari)
    if dosen is None:
        raise galat(503, "Prodi terbuka belum siap: dosen PA/kaprodi belum ditetapkan.")

    email = body.email.strip().lower()
    if _email_cadangan(email):
        raise galat(409, "Email tidak dapat dipakai.")
    pesan = validasi_kebijakan_sandi(body.sandi, email)
    if pesan:
        raise galat(400, pesan)
    if db.scalar(select(Akun.id).where(func.lower(Akun.email) == email)):
        raise galat(409, "Email sudah terdaftar.")

    try:
        orang, akun = buat_mahasiswa(
            db,
            nama_lengkap=body.nama_lengkap,
            email=email,
            sandi_hash=hash_sandi(body.sandi),
            prodi=prodi,
            dosen_id=dosen.id,
            hari=hari,
            prodi_isian=body.program_studi,
            pt_isian=body.perguruan_tinggi,
            pelaku_id=None,
        )
        token = terbitkan_token(db, akun, hari)
        catat_registrasi()
        db.commit()
    except IntegrityError:
        db.rollback()
        raise galat(409, "Email sudah terdaftar.") from None
    return token


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, request: Request, db: DB, hari: Hari) -> dict:
    email = body.email.strip().lower()
    kunci = f"{email}|{alamat_klien(request)}"
    if terlalu_banyak_gagal(kunci):
        raise galat(429, "Terlalu banyak percobaan. Coba lagi beberapa menit lagi.")

    akun = db.scalar(select(Akun).where(func.lower(Akun.email) == email))
    sandi_ok = cek_sandi(body.sandi, akun.sandi_hash if akun else None)
    if akun is None or not sandi_ok or akun.status != "aktif":
        catat_gagal(kunci)
        raise galat(401, GALAT_LOGIN)

    token = terbitkan_token(db, akun, hari)
    akun.login_terakhir = datetime.now(UTC)
    db.commit()
    reset_gagal(kunci)
    return token


@router.post("/refresh", response_model=TokenOut)
def refresh(body: RefreshIn, db: DB, hari: Hari) -> dict:
    rt = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_refresh(body.refresh_token)))
    if rt is None:
        raise galat(401, "Token tidak ada atau tidak valid")
    if rt.dicabut is not None:
        # Token yang sudah dipakai muncul lagi: kemungkinan dicuri. Cabut semua sesi akun ini.
        cabut_semua_refresh(db, rt.akun_id)
        db.commit()
        raise galat(401, "Token tidak ada atau tidak valid")
    if rt.kedaluwarsa <= datetime.now(UTC):
        raise galat(401, "Token kedaluwarsa")

    akun = db.get(Akun, rt.akun_id)
    if akun is None or akun.status != "aktif":
        raise galat(401, "Token tidak ada atau tidak valid")

    rt.dicabut = datetime.now(UTC)  # sekali pakai (rotasi)
    token = terbitkan_token(db, akun, hari)
    db.commit()
    return token


@router.post("/logout", status_code=204)
def logout(body: LogoutIn, saya: SayaBebas, db: DB) -> Response:
    if body.refresh_token:
        rt = db.scalar(
            select(RefreshToken).where(
                RefreshToken.token_hash == hash_refresh(body.refresh_token),
                RefreshToken.akun_id == saya.akun.id,
            )
        )
        if rt is not None and rt.dicabut is None:
            rt.dicabut = datetime.now(UTC)
            db.commit()
    return Response(status_code=204)


@router.post("/ganti-sandi", response_model=TokenOut)
def ganti_sandi(body: GantiSandiIn, saya: SayaBebas, db: DB, hari: Hari) -> dict:
    akun = saya.akun
    if not cek_sandi(body.sandi_lama, akun.sandi_hash):
        raise galat(400, "Sandi lama salah.")
    pesan = validasi_kebijakan_sandi(body.sandi_baru, akun.email)
    if pesan:
        raise galat(400, pesan)
    if body.sandi_baru == body.sandi_lama:
        raise galat(400, "Sandi baru harus berbeda dari sandi lama.")

    akun.sandi_hash = hash_sandi(body.sandi_baru)
    akun.wajib_ganti_sandi = False
    akun.versi_token += 1  # semua access token lama langsung tidak sah
    cabut_semua_refresh(db, akun.id)
    audit.catat(db, saya.orang_id, "akun.ganti_sandi", "akun", akun.id)
    token = terbitkan_token(db, akun, hari)
    db.commit()
    return token


@router.get("/saya")
def saya_profil(saya: SayaBebas, db: DB, hari: Hari) -> dict:
    cak = saya.cakupan
    orang = saya.orang

    # Nama unit supaya klien tidak perlu mencarinya satu per satu.
    unit: list[dict] = []
    for s in cak.scopes:
        item = dict(s)
        if s.get("id"):
            model = {"fakultas": Fakultas, "jurusan": Jurusan, "prodi": Prodi}[s["tipe"]]
            obj = db.get(model, uuid.UUID(s["id"]))
            item["nama"] = obj.nama if obj else None
        unit.append(item)

    hasil: dict = {
        "id": str(orang.id),
        "akun_id": str(saya.akun.id),
        "nama_lengkap": orang.nama_lengkap,
        "nim": orang.nim,
        "nidn": orang.nidn,
        "email": saya.akun.email,
        "prodi_isian": orang.prodi_isian,
        "pt_isian": orang.pt_isian,
        "wajib_ganti_sandi": saya.akun.wajib_ganti_sandi,
        "peran": cak.peran,
        "unit": unit,
        "pembimbing_akademik": None,
        "kaprodi": None,
        "panduan_pribadi": bool(
            cak.prodi_mahasiswa is not None and adalah_prodi_terbuka(db, cak.prodi_mahasiswa)
        ),
    }
    hasil["akademik"] = None
    if cak.prodi_mahasiswa is not None:
        prodi = db.get(Prodi, cak.prodi_mahasiswa)
        jurusan = db.get(Jurusan, prodi.jurusan_id) if prodi else None
        fakultas = db.get(Fakultas, jurusan.fakultas_id) if jurusan else None
        if prodi:
            anggota = db.scalar(
                select(KeanggotaanProdi).where(
                    KeanggotaanProdi.orang_id == orang.id, KeanggotaanProdi.selesai.is_(None)
                )
            )
            hasil["akademik"] = {
                "prodi": {
                    "id": str(prodi.id),
                    "kode": prodi.kode,
                    "nama": prodi.nama,
                    "jenjang": prodi.jenjang,
                    "terbuka": adalah_prodi_terbuka(db, prodi.id),
                },
                "jurusan": {"kode": jurusan.kode, "nama": jurusan.nama} if jurusan else None,
                "fakultas": {"kode": fakultas.kode, "nama": fakultas.nama} if fakultas else None,
                "angkatan": anggota.angkatan if anggota else None,
                "status": anggota.status if anggota else None,
            }
        pa = db.scalar(
            select(Orang)
            .join(Bimbingan, Bimbingan.dosen_id == Orang.id)
            .where(Bimbingan.mahasiswa_id == orang.id, Bimbingan.selesai.is_(None))
        )
        if pa:
            hasil["pembimbing_akademik"] = {"id": str(pa.id), "nama_lengkap": pa.nama_lengkap}
        kp = db.scalar(
            select(Orang)
            .join(Penugasan, Penugasan.orang_id == Orang.id)
            .where(
                Penugasan.peran == "kaprodi",
                Penugasan.unit_id == cak.prodi_mahasiswa,
                penugasan_aktif(hari),
            )
        )
        if kp:
            hasil["kaprodi"] = {"id": str(kp.id), "nama_lengkap": kp.nama_lengkap}
    return hasil
