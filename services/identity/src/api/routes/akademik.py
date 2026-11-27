"""Konteks akademik: prodi, pembimbing akademik, dan panduan aktif seorang mahasiswa.

Dipakai layanan rekomendasi (matkul) sebagai sumber tunggal, sehingga dasar rekomendasi
selalu panduan prodi mahasiswa itu sendiri, bukan berkas yang diunggah pengguna.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query
from sqlalchemy import select

from src.api.deps import DB, Hari, Saya
from src.api.errors import dilarang, galat, tidak_ditemukan
from src.domain.panduan_berlaku import pesan_tanpa_panduan, panduan_berlaku
from src.domain.prodi_terbuka import adalah_prodi_terbuka
from src.models import Akun, Bimbingan, Fakultas, Jurusan, Orang, Prodi

router = APIRouter(prefix="/akademik", tags=["akademik"])


@router.get("/konteks")
def konteks(
    saya: Saya,
    db: DB,
    hari: Hari,
    tanpa_teks: bool = Query(False, description="Lewati isi teks panduan (lebih ringan untuk tampilan)"),
    prodi_id: uuid.UUID | None = Query(None, description="Khusus staf: lihat konteks sebuah prodi"),
) -> dict:
    cak = saya.cakupan
    mahasiswa = None
    pa = None
    mahasiswa_id = None

    if cak.prodi_mahasiswa is not None:
        target_prodi = cak.prodi_mahasiswa
        mahasiswa_id = saya.orang.id
        mahasiswa = {"id": str(saya.orang.id), "nama_lengkap": saya.orang.nama_lengkap, "nim": saya.orang.nim}
        dosen = db.scalar(
            select(Orang)
            .join(Bimbingan, Bimbingan.dosen_id == Orang.id)
            .where(Bimbingan.mahasiswa_id == saya.orang.id, Bimbingan.selesai.is_(None))
        )
        if dosen is not None:
            akun_dosen = db.scalar(select(Akun).where(Akun.orang_id == dosen.id))
            pa = {
                "id": str(dosen.id),
                "nama_lengkap": dosen.nama_lengkap,
                # Email akun dosen = identitas penerima tugas di Tasklist AlurKerja.
                "email": akun_dosen.email if akun_dosen else dosen.email_kontak,
            }
    else:
        # Staf (kaprodi, kajur, dekan, superadmin) boleh melihat konteks prodi dalam cakupannya.
        if prodi_id is None:
            raise dilarang("Konteks akademik hanya untuk mahasiswa. Staf wajib menyertakan prodi_id.")
        if not cak.lihat_prodi(prodi_id):
            raise tidak_ditemukan("Prodi")
        target_prodi = prodi_id

    prodi = db.get(Prodi, target_prodi)
    if prodi is None:
        raise tidak_ditemukan("Prodi")
    jurusan = db.get(Jurusan, prodi.jurusan_id)
    fakultas = db.get(Fakultas, jurusan.fakultas_id) if jurusan else None
    terbuka = adalah_prodi_terbuka(db, prodi.id)
    panduan_pribadi = terbuka and mahasiswa_id is not None

    panduan = panduan_berlaku(db, prodi.id, mahasiswa_id)
    # Prodi dummy tanpa panduan pribadi: tetap 200 agar UI bisa menampilkan unggah (kecuali teks wajib).
    if panduan is None and not (panduan_pribadi and tanpa_teks):
        raise galat(404, pesan_tanpa_panduan(db, prodi.id, prodi.nama))
    if panduan is None and not tanpa_teks:
        raise galat(404, pesan_tanpa_panduan(db, prodi.id, prodi.nama))

    hasil_panduan = None
    if panduan is not None:
        hasil_panduan = {
            "id": str(panduan.id),
            "versi": panduan.versi,
            "judul": panduan.judul,
            "berlaku_mulai": panduan.berlaku_mulai.isoformat() if panduan.berlaku_mulai else None,
            "teks_karakter": panduan.teks_karakter,
            "pribadi": panduan.pemilik_id is not None,
        }
        if not tanpa_teks:
            if not panduan.teks:
                raise galat(409, "Panduan aktif belum memiliki teks hasil ekstraksi. Unggah ulang panduan.")
            hasil_panduan["teks"] = panduan.teks

    return {
        "mahasiswa": mahasiswa,
        "prodi": {
            "id": str(prodi.id),
            "kode": prodi.kode,
            "nama": prodi.nama,
            "jenjang": prodi.jenjang,
            "maks_sks_semester": prodi.maks_sks_semester,
            "terbuka": terbuka,
            "jurusan": {"id": str(jurusan.id), "kode": jurusan.kode, "nama": jurusan.nama} if jurusan else None,
            "fakultas": {"id": str(fakultas.id), "kode": fakultas.kode, "nama": fakultas.nama} if fakultas else None,
        },
        "pembimbing_akademik": pa,
        "panduan": hasil_panduan,
        "panduan_pribadi": panduan_pribadi,
    }
