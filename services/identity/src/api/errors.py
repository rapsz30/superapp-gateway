"""Galat API. Semua respons galat berbentuk {"detail": "pesan"}."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError


def galat(status: int, pesan: str) -> HTTPException:
    return HTTPException(status_code=status, detail=pesan)


def tidak_ditemukan(apa: str = "Data") -> HTTPException:
    # Sengaja sama untuk "tidak ada" dan "di luar cakupan", agar keberadaan data tidak bocor.
    return galat(404, f"{apa} tidak ditemukan")


def dilarang(pesan: str = "Akses ditolak") -> HTTPException:
    return galat(403, pesan)


PESAN_BATASAN = {
    "uq_dekan_aktif": "Fakultas ini sudah memiliki dekan aktif. Akhiri penugasan lama terlebih dahulu.",
    "uq_kajur_aktif": "Jurusan ini sudah memiliki kajur aktif. Akhiri penugasan lama terlebih dahulu.",
    "uq_kaprodi_aktif": "Prodi ini sudah memiliki kaprodi aktif. Akhiri penugasan lama terlebih dahulu.",
    "uq_penugasan_orang_unit_aktif": "Orang ini sudah memiliki penugasan aktif yang sama.",
    "uq_bimbingan_aktif": "Mahasiswa ini sudah memiliki dosen PA aktif.",
    "uq_keanggotaan_aktif": "Orang ini sudah terdaftar aktif di sebuah prodi.",
    "uq_pengajuan_terbuka": "Anda masih memiliki pengajuan yang menunggu keputusan. Batalkan atau tunggu keputusannya.",
    "uq_panduan_aktif": "Prodi ini sudah memiliki panduan aktif.",
    "uq_panduan_versi": "Versi panduan bentrok. Ulangi permintaan.",
    "uq_akun_email_lower": "Email sudah dipakai akun lain.",
    "akun_orang_id_key": "Orang ini sudah memiliki akun.",
    "orang_nim_key": "NIM sudah dipakai.",
    "orang_nidn_key": "NIDN sudah dipakai.",
    "fakultas_kode_key": "Kode fakultas sudah dipakai.",
    "uq_jurusan_kode": "Kode jurusan sudah dipakai di fakultas ini.",
    "uq_prodi_kode": "Kode prodi sudah dipakai di jurusan ini.",
    "ck_penugasan_peran_unit": "Peran dan tipe unit tidak cocok.",
    "ck_bimbingan_diri": "Dosen tidak boleh membimbing dirinya sendiri.",
    "ck_penugasan_tanggal": "Tanggal selesai tidak boleh sebelum tanggal mulai.",
    "ck_keanggotaan_tanggal": "Tanggal selesai tidak boleh sebelum tanggal mulai.",
    "ck_bimbingan_tanggal": "Tanggal selesai tidak boleh sebelum tanggal mulai.",
}


def pasang_penangan(app: FastAPI) -> None:
    @app.exception_handler(IntegrityError)
    async def _integritas(_: Request, exc: IntegrityError) -> JSONResponse:
        diag = getattr(exc.orig, "diag", None)
        nama = getattr(diag, "constraint_name", None)
        kode = getattr(exc.orig, "pgcode", "")
        pesan = PESAN_BATASAN.get(nama or "")
        if kode == "23514":  # check_violation
            return JSONResponse(status_code=400, content={"detail": pesan or "Data tidak valid."})
        return JSONResponse(
            status_code=409,
            content={"detail": pesan or "Data melanggar aturan keunikan atau relasi."},
        )
