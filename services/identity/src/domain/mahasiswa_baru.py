"""Pembuatan mahasiswa prodi dummy (registrasi publik dan batch dummy)."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.domain import audit
from src.models import Akun, Bimbingan, KeanggotaanProdi, Orang, Prodi

DOMAIN_DUMMY = "studentgateway.id"
AWALAN_NIM = "98"
MAKS_COBA_NIM = 20


def _tahun_dua(hari: date) -> str:
    return f"{hari.year % 100:02d}"


def _nim_berikut(db: Session, hari: date) -> str:
    awalan = f"{AWALAN_NIM}{_tahun_dua(hari)}"
    # Ambil angka urut tertinggi yang sudah dipakai untuk awalan ini.
    pola = f"{awalan}%"
    terakhir = db.scalar(
        select(func.max(Orang.nim)).where(Orang.nim.like(pola), func.length(Orang.nim) == len(awalan) + 6)
    )
    if terakhir and terakhir[len(awalan) :].isdigit():
        urut = int(terakhir[len(awalan) :]) + 1
    else:
        urut = 1
    return f"{awalan}{urut:06d}"


def buat_mahasiswa(
    db: Session,
    *,
    nama_lengkap: str,
    email: str,
    sandi_hash: str,
    prodi: Prodi,
    dosen_id: uuid.UUID,
    hari: date,
    prodi_isian: str | None,
    pt_isian: str | None,
    pelaku_id: uuid.UUID | None,
) -> tuple[Orang, Akun]:
    """Buat orang, akun, keanggotaan, dan bimbingan dalam transaksi pemanggil.

    Memakai savepoint saat bentrok NIM. `sandi_hash` sudah dihitung pemanggil
    (boleh dipakai ulang untuk batch).
    """
    terakhir_exc: Exception | None = None
    for _ in range(MAKS_COBA_NIM):
        nim = _nim_berikut(db, hari)
        try:
            with db.begin_nested():
                orang = Orang(
                    nama_lengkap=nama_lengkap,
                    nim=nim,
                    prodi_isian=prodi_isian,
                    pt_isian=pt_isian,
                    email_kontak=email,
                )
                db.add(orang)
                db.flush()

                akun = Akun(
                    orang_id=orang.id,
                    email=email,
                    sandi_hash=sandi_hash,
                    wajib_ganti_sandi=False,
                    status="aktif",
                )
                db.add(akun)
                db.flush()

                anggota = KeanggotaanProdi(
                    orang_id=orang.id,
                    prodi_id=prodi.id,
                    angkatan=hari.year,
                    status="aktif",
                    mulai=hari,
                )
                db.add(anggota)
                db.flush()

                bimbingan = Bimbingan(
                    dosen_id=dosen_id,
                    mahasiswa_id=orang.id,
                    mulai=hari,
                )
                db.add(bimbingan)
                db.flush()

                audit.catat(db, pelaku_id, "orang.buat", "orang", orang.id, None, audit.ke_dict(orang))
                audit.catat(db, pelaku_id, "akun.buat", "akun", akun.id, None, audit.ke_dict(akun))
                audit.catat(
                    db, pelaku_id, "keanggotaan.buat", "keanggotaan_prodi", anggota.id, None, audit.ke_dict(anggota)
                )
                audit.catat(
                    db, pelaku_id, "bimbingan.buat", "bimbingan", bimbingan.id, None, audit.ke_dict(bimbingan)
                )
                return orang, akun
        except IntegrityError as exc:
            terakhir_exc = exc
            # Nim bentrok: isi ulang urutan. Email bentrok harus naik ke pemanggil.
            diag = getattr(exc.orig, "diag", None)
            nama = getattr(diag, "constraint_name", None) or ""
            if nama in ("orang_nim_key", "orang_nim_key".upper()) or "nim" in nama.lower():
                # Pastikan max terlihat setelah gagal: kunci sementara tidak perlu.
                db.execute(text("SELECT 1"))
                continue
            raise
    raise terakhir_exc or RuntimeError("Gagal membuat NIM unik")


def nomor_mahasiswa_berikut(db: Session) -> int:
    """Angka lanjut untuk email mahasiswaN@studentgateway.id (minimal 1)."""
    pola = f"mahasiswa%@{DOMAIN_DUMMY}"
    emails = db.scalars(select(Akun.email).where(func.lower(Akun.email).like(pola))).all()
    tertinggi = 0
    for e in emails:
        lokal = e.split("@", 1)[0].lower()
        if lokal.startswith("mahasiswa") and lokal[9:].isdigit():
            tertinggi = max(tertinggi, int(lokal[9:]))
    return tertinggi + 1
