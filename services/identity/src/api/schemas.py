"""Skema permintaan dan respons."""

from __future__ import annotations

import re
import uuid
from datetime import date, datetime
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

Kode = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32, pattern=r"^[A-Za-z0-9._-]+$")
]
Nama = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Jenjang = Literal["D3", "S1", "S2", "S3", "Profesi"]
Peran = Literal["superadmin", "dekan", "kajur", "kaprodi", "dosen_pa"]
UnitTipe = Literal["global", "fakultas", "jurusan", "prodi"]

PASANGAN_SAH = {
    "superadmin": {"global"},
    "dekan": {"fakultas"},
    "kajur": {"jurusan"},
    "kaprodi": {"prodi"},
    "dosen_pa": {"prodi", "jurusan"},
}


class Dasar(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")


class Halaman(BaseModel):
    data: list[Any]
    total: int


# ---------- Auth ----------
class LoginIn(Dasar):
    # Sengaja str biasa: login tidak boleh menolak alamat internal yang sudah terdaftar.
    email: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=255)]
    sandi: str = Field(min_length=1, max_length=200)


class RefreshIn(Dasar):
    refresh_token: str = Field(min_length=10, max_length=200)


class LogoutIn(Dasar):
    refresh_token: str | None = Field(default=None, max_length=200)


class GantiSandiIn(Dasar):
    sandi_lama: str = Field(min_length=1, max_length=200)
    sandi_baru: str = Field(min_length=1, max_length=200)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: str
    wajib_ganti_sandi: bool
    peran: list[str]


# ---------- Struktur ----------
class FakultasIn(Dasar):
    kode: Kode
    nama: Nama


class FakultasPatch(Dasar):
    nama: Nama | None = None
    aktif: bool | None = None


class FakultasOut(Dasar):
    id: uuid.UUID
    kode: str
    nama: str
    aktif: bool


class JurusanIn(Dasar):
    fakultas_id: uuid.UUID
    kode: Kode
    nama: Nama


class JurusanOut(Dasar):
    id: uuid.UUID
    fakultas_id: uuid.UUID
    kode: str
    nama: str
    aktif: bool


class ProdiIn(Dasar):
    jurusan_id: uuid.UUID
    kode: Kode
    nama: Nama
    jenjang: Jenjang = "S1"
    maks_sks_semester: int | None = Field(default=None, ge=1, le=40)


class ProdiPatch(Dasar):
    nama: Nama | None = None
    jenjang: Jenjang | None = None
    maks_sks_semester: int | None = Field(default=None, ge=1, le=40)
    aktif: bool | None = None


class ProdiOut(Dasar):
    id: uuid.UUID
    jurusan_id: uuid.UUID
    kode: str
    nama: str
    jenjang: str
    maks_sks_semester: int | None = None
    aktif: bool


# ---------- Orang dan akun ----------
_NOMOR = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)]


class OrangIn(Dasar):
    nama_lengkap: Nama
    nim: _NOMOR | None = None
    nidn: _NOMOR | None = None
    email_kontak: EmailStr | None = None


class OrangPatch(Dasar):
    nama_lengkap: Nama | None = None
    nim: _NOMOR | None = None
    nidn: _NOMOR | None = None
    email_kontak: EmailStr | None = None


class AkunRingkas(BaseModel):
    id: uuid.UUID
    email: str
    status: str
    wajib_ganti_sandi: bool


class OrangOut(BaseModel):
    id: uuid.UUID
    nama_lengkap: str
    nim: str | None = None
    nidn: str | None = None
    email_kontak: str | None = None
    peran: list[str] = []
    akun: AkunRingkas | None = None


class AkunIn(Dasar):
    orang_id: uuid.UUID
    email: EmailStr
    sandi: str | None = Field(default=None, max_length=200)

    @field_validator("email")
    @classmethod
    def _huruf_kecil(cls, v: str) -> str:
        return v.strip().lower()


class AkunOut(BaseModel):
    id: uuid.UUID
    orang_id: uuid.UUID
    email: str
    status: str
    wajib_ganti_sandi: bool
    sandi_sementara: str | None = None


class AkunStatusIn(Dasar):
    status: Literal["aktif", "ditangguhkan", "nonaktif"]


# ---------- Penugasan, keanggotaan, bimbingan ----------
class PenugasanIn(Dasar):
    orang_id: uuid.UUID
    peran: Peran
    unit_tipe: UnitTipe
    unit_id: uuid.UUID | None = None
    mulai: date | None = None

    @model_validator(mode="after")
    def _periksa_pasangan(self) -> PenugasanIn:
        if self.unit_tipe not in PASANGAN_SAH[self.peran]:
            raise ValueError(f"Peran {self.peran} tidak berlaku untuk unit {self.unit_tipe}.")
        if (self.unit_tipe == "global") != (self.unit_id is None):
            raise ValueError("unit_id wajib untuk unit non-global dan harus kosong untuk global.")
        return self


class AkhiriIn(Dasar):
    selesai: date | None = None


class PenugasanOut(Dasar):
    id: uuid.UUID
    orang_id: uuid.UUID
    peran: str
    unit_tipe: str
    unit_id: uuid.UUID | None
    mulai: date
    selesai: date | None


class KeanggotaanIn(Dasar):
    orang_id: uuid.UUID
    prodi_id: uuid.UUID
    angkatan: int | None = Field(default=None, ge=1990, le=2100)
    status: Literal["aktif", "cuti"] = "aktif"
    mulai: date | None = None


class KeanggotaanStatusIn(Dasar):
    status: Literal["aktif", "cuti", "lulus", "keluar"]
    tanggal: date | None = None


class KeanggotaanPindahIn(Dasar):
    prodi_tujuan_id: uuid.UUID
    angkatan: int | None = Field(default=None, ge=1990, le=2100)
    tanggal: date | None = None


class KeanggotaanOut(Dasar):
    id: uuid.UUID
    orang_id: uuid.UUID
    prodi_id: uuid.UUID
    angkatan: int | None
    status: str
    mulai: date
    selesai: date | None


class BimbinganIn(Dasar):
    dosen_id: uuid.UUID
    mahasiswa_id: uuid.UUID
    mulai: date | None = None


class BimbinganPindahIn(Dasar):
    dosen_asal_id: uuid.UUID
    dosen_tujuan_id: uuid.UUID
    mahasiswa_ids: list[uuid.UUID] | None = Field(default=None, max_length=2000)


class BimbinganOut(Dasar):
    id: uuid.UUID
    dosen_id: uuid.UUID
    mahasiswa_id: uuid.UUID
    mulai: date
    selesai: date | None


# ---------- Panduan ----------
class PanduanOut(Dasar):
    id: uuid.UUID
    prodi_id: uuid.UUID
    versi: int
    judul: str
    berlaku_mulai: date | None
    status: str
    berkas_nama: str
    teks_karakter: int | None = None


class AuditOut(Dasar):
    id: int
    pelaku_id: uuid.UUID | None
    aksi: str
    objek_tipe: str
    objek_id: uuid.UUID | None
    sebelum: dict | None
    sesudah: dict | None
    waktu: datetime


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def email_sah(v: str) -> bool:
    return bool(_EMAIL_RE.match(v))


# ---------- Pengajuan ----------
class KeputusanIn(Dasar):
    keputusan: Literal["setuju", "revisi"]
    catatan: str | None = Field(default=None, max_length=2000)
