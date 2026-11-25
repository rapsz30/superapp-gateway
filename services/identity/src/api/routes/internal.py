"""Endpoint internal untuk gateway. Tidak boleh terjangkau dari luar.

Dilindungi dua lapis: NGINX menjawab 404 untuk /api/identity/internal/*, dan setiap
permintaan wajib membawa X-Internal-Token yang sama dengan INTERNAL_TOKEN.
"""

from __future__ import annotations

import hmac
import uuid

from fastapi import APIRouter, Header
from sqlalchemy import select

from src.api.deps import DB
from src.api.errors import tidak_ditemukan
from src.core.config import get_settings
from src.models import Akun, Orang, PanduanAkademik, Pengajuan, Prodi

router = APIRouter(prefix="/internal", tags=["internal"], include_in_schema=False)


@router.get("/akun/{akun_id}/versi-token")
def versi_token(akun_id: uuid.UUID, db: DB, x_internal_token: str = Header("")) -> dict:
    """Dipakai verifier gateway untuk mematikan token akun yang ditangguhkan atau berganti sandi."""
    rahasia = get_settings().internal_token
    # Tanpa INTERNAL_TOKEN endpoint dianggap tidak ada. compare_digest mencegah tebakan lewat waktu respons.
    if not rahasia or not hmac.compare_digest(x_internal_token.encode(), rahasia.encode()):
        raise tidak_ditemukan("Halaman")
    akun = db.get(Akun, akun_id)
    if akun is None:
        raise tidak_ditemukan("Akun")
    return {"versi_token": akun.versi_token, "status": akun.status}


def _periksa_token(token: str) -> None:
    rahasia = get_settings().internal_token
    if not rahasia or not hmac.compare_digest(token.encode(), rahasia.encode()):
        raise tidak_ditemukan("Halaman")


@router.get("/pengajuan/{pengajuan_id}/konteks")
def konteks_pengajuan(pengajuan_id: uuid.UUID, db: DB, x_internal_token: str = Header("")) -> dict:
    """Dipakai layanan matkul saat langkah ekstraksi: prodi, NIM akun, dan panduan AKTIF prodi itu.

    Versi panduan yang dikembalikan di sini adalah versi yang dipakai untuk seluruh proses (matkul
    menyimpannya bersama KHS), sehingga dicatat pada pengajuan.
    """
    _periksa_token(x_internal_token)
    p = db.get(Pengajuan, pengajuan_id)
    if p is None:
        raise tidak_ditemukan("Pengajuan")
    prodi = db.get(Prodi, p.prodi_id)
    mhs = db.get(Orang, p.mahasiswa_id)
    panduan = db.scalar(
        select(PanduanAkademik).where(PanduanAkademik.prodi_id == p.prodi_id, PanduanAkademik.status == "aktif")
    )
    if prodi is None or panduan is None or not panduan.teks:
        raise tidak_ditemukan("Panduan aktif")
    if p.status == "diajukan" and (p.panduan_id != panduan.id):
        p.panduan_id, p.panduan_versi = panduan.id, panduan.versi
        db.commit()
    return {
        "mahasiswa": {"nim": mhs.nim if mhs else None},
        "prodi": {"id": str(prodi.id), "kode": prodi.kode, "nama": prodi.nama, "maks_sks_semester": prodi.maks_sks_semester},
        "panduan": {"id": str(panduan.id), "versi": panduan.versi, "teks": panduan.teks},
    }
