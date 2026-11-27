"""Model database layanan identity.

Aturan jumlah (satu kaprodi aktif, satu PA aktif, dst.) ditegakkan oleh indeks unik
parsial dan CHECK. Definisi yang sama ada di migrasi Alembic 0001.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

PERAN = ("superadmin", "dekan", "kajur", "kaprodi", "dosen_pa")
UNIT_TIPE = ("global", "fakultas", "jurusan", "prodi")
JENJANG = ("D3", "S1", "S2", "S3", "Profesi")
STATUS_AKUN = ("aktif", "ditangguhkan", "nonaktif")
STATUS_KEANGGOTAAN = ("aktif", "cuti", "lulus", "keluar", "pindah")
STATUS_PANDUAN = ("draf", "aktif", "diarsipkan")


class Base(DeclarativeBase):
    pass


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid())


def _dibuat() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Fakultas(Base):
    __tablename__ = "fakultas"
    id: Mapped[uuid.UUID] = _uuid_pk()
    kode: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    nama: Mapped[str] = mapped_column(String(200), nullable=False)
    aktif: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    dibuat: Mapped[datetime] = _dibuat()


class Jurusan(Base):
    __tablename__ = "jurusan"
    __table_args__ = (UniqueConstraint("fakultas_id", "kode", name="uq_jurusan_kode"),)
    id: Mapped[uuid.UUID] = _uuid_pk()
    fakultas_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("fakultas.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    kode: Mapped[str] = mapped_column(String(32), nullable=False)
    nama: Mapped[str] = mapped_column(String(200), nullable=False)
    aktif: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    dibuat: Mapped[datetime] = _dibuat()


class Prodi(Base):
    __tablename__ = "prodi"
    __table_args__ = (
        UniqueConstraint("jurusan_id", "kode", name="uq_prodi_kode"),
        CheckConstraint("jenjang IN ('D3','S1','S2','S3','Profesi')", name="ck_prodi_jenjang"),
        CheckConstraint(
            "maks_sks_semester IS NULL OR maks_sks_semester BETWEEN 1 AND 40", name="ck_prodi_maks_sks"
        ),
    )
    id: Mapped[uuid.UUID] = _uuid_pk()
    jurusan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jurusan.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    kode: Mapped[str] = mapped_column(String(32), nullable=False)
    nama: Mapped[str] = mapped_column(String(200), nullable=False)
    jenjang: Mapped[str] = mapped_column(String(16), nullable=False, server_default="S1")
    # Batas beban studi per semester menurut panduan prodi; kosong = bawaan layanan rekomendasi (24).
    maks_sks_semester: Mapped[int | None] = mapped_column(Integer)
    aktif: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    dibuat: Mapped[datetime] = _dibuat()


class Orang(Base):
    __tablename__ = "orang"
    id: Mapped[uuid.UUID] = _uuid_pk()
    nama_lengkap: Mapped[str] = mapped_column(String(200), nullable=False)
    nim: Mapped[str | None] = mapped_column(String(32), unique=True)
    nidn: Mapped[str | None] = mapped_column(String(32), unique=True)
    email_kontak: Mapped[str | None] = mapped_column(String(255))
    # Catatan bebas dari formulir registrasi (bukan struktur kampus).
    prodi_isian: Mapped[str | None] = mapped_column(String(200))
    pt_isian: Mapped[str | None] = mapped_column(String(200))
    dibuat: Mapped[datetime] = _dibuat()


class Akun(Base):
    __tablename__ = "akun"
    __table_args__ = (
        Index("uq_akun_email_lower", text("lower(email)"), unique=True),
        CheckConstraint("status IN ('aktif','ditangguhkan','nonaktif')", name="ck_akun_status"),
    )
    id: Mapped[uuid.UUID] = _uuid_pk()
    orang_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orang.id", ondelete="RESTRICT"), unique=True, nullable=False
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    sandi_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="aktif")
    wajib_ganti_sandi: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    versi_token: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    login_terakhir: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dibuat: Mapped[datetime] = _dibuat()


class RefreshToken(Base):
    __tablename__ = "refresh_token"
    id: Mapped[uuid.UUID] = _uuid_pk()
    akun_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("akun.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    kedaluwarsa: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    dicabut: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dibuat: Mapped[datetime] = _dibuat()


class Penugasan(Base):
    __tablename__ = "penugasan"
    __table_args__ = (
        CheckConstraint(
            "peran IN ('superadmin','dekan','kajur','kaprodi','dosen_pa')",
            name="ck_penugasan_peran",
        ),
        CheckConstraint(
            "unit_tipe IN ('global','fakultas','jurusan','prodi')", name="ck_penugasan_unit_tipe"
        ),
        CheckConstraint("(unit_tipe = 'global') = (unit_id IS NULL)", name="ck_penugasan_unit_id"),
        CheckConstraint(
            "(peran = 'superadmin' AND unit_tipe = 'global')"
            " OR (peran = 'dekan' AND unit_tipe = 'fakultas')"
            " OR (peran = 'kajur' AND unit_tipe = 'jurusan')"
            " OR (peran = 'kaprodi' AND unit_tipe = 'prodi')"
            " OR (peran = 'dosen_pa' AND unit_tipe IN ('prodi','jurusan'))",
            name="ck_penugasan_peran_unit",
        ),
        CheckConstraint("selesai IS NULL OR selesai >= mulai", name="ck_penugasan_tanggal"),
        Index(
            "uq_dekan_aktif",
            "unit_id",
            unique=True,
            postgresql_where=text("peran = 'dekan' AND selesai IS NULL"),
        ),
        Index(
            "uq_kajur_aktif",
            "unit_id",
            unique=True,
            postgresql_where=text("peran = 'kajur' AND selesai IS NULL"),
        ),
        Index(
            "uq_kaprodi_aktif",
            "unit_id",
            unique=True,
            postgresql_where=text("peran = 'kaprodi' AND selesai IS NULL"),
        ),
        Index(
            "uq_penugasan_orang_unit_aktif",
            "orang_id",
            "peran",
            "unit_id",
            unique=True,
            postgresql_where=text("selesai IS NULL AND unit_id IS NOT NULL"),
        ),
    )
    id: Mapped[uuid.UUID] = _uuid_pk()
    orang_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orang.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    peran: Mapped[str] = mapped_column(String(16), nullable=False)
    unit_tipe: Mapped[str] = mapped_column(String(16), nullable=False)
    unit_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    mulai: Mapped[date] = mapped_column(Date, nullable=False)
    selesai: Mapped[date | None] = mapped_column(Date)
    dibuat_oleh: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("orang.id"))
    dibuat: Mapped[datetime] = _dibuat()


class KeanggotaanProdi(Base):
    __tablename__ = "keanggotaan_prodi"
    __table_args__ = (
        CheckConstraint(
            "status IN ('aktif','cuti','lulus','keluar','pindah')", name="ck_keanggotaan_status"
        ),
        CheckConstraint("selesai IS NULL OR selesai >= mulai", name="ck_keanggotaan_tanggal"),
        CheckConstraint(
            "(selesai IS NULL) = (status IN ('aktif','cuti'))", name="ck_keanggotaan_status_selesai"
        ),
        Index(
            "uq_keanggotaan_aktif",
            "orang_id",
            unique=True,
            postgresql_where=text("selesai IS NULL"),
        ),
    )
    id: Mapped[uuid.UUID] = _uuid_pk()
    orang_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orang.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    prodi_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("prodi.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    angkatan: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="aktif")
    mulai: Mapped[date] = mapped_column(Date, nullable=False)
    selesai: Mapped[date | None] = mapped_column(Date)
    dibuat: Mapped[datetime] = _dibuat()


class Bimbingan(Base):
    __tablename__ = "bimbingan"
    __table_args__ = (
        CheckConstraint("dosen_id <> mahasiswa_id", name="ck_bimbingan_diri"),
        CheckConstraint("selesai IS NULL OR selesai >= mulai", name="ck_bimbingan_tanggal"),
        Index(
            "uq_bimbingan_aktif",
            "mahasiswa_id",
            unique=True,
            postgresql_where=text("selesai IS NULL"),
        ),
    )
    id: Mapped[uuid.UUID] = _uuid_pk()
    dosen_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orang.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    mahasiswa_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orang.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    mulai: Mapped[date] = mapped_column(Date, nullable=False)
    selesai: Mapped[date | None] = mapped_column(Date)
    dibuat: Mapped[datetime] = _dibuat()


class PanduanAkademik(Base):
    __tablename__ = "panduan_akademik"
    __table_args__ = (
        CheckConstraint("status IN ('draf','aktif','diarsipkan')", name="ck_panduan_status"),
        # Panduan prodi (pemilik_id NULL): satu aktif dan versi unik per prodi.
        Index(
            "uq_panduan_aktif",
            "prodi_id",
            unique=True,
            postgresql_where=text("status = 'aktif' AND pemilik_id IS NULL"),
        ),
        Index(
            "uq_panduan_versi",
            "prodi_id",
            "versi",
            unique=True,
            postgresql_where=text("pemilik_id IS NULL"),
        ),
        # Panduan pribadi: satu aktif dan versi unik per pemilik.
        Index(
            "uq_panduan_aktif_pemilik",
            "pemilik_id",
            unique=True,
            postgresql_where=text("status = 'aktif' AND pemilik_id IS NOT NULL"),
        ),
        Index(
            "uq_panduan_versi_pemilik",
            "pemilik_id",
            "versi",
            unique=True,
            postgresql_where=text("pemilik_id IS NOT NULL"),
        ),
    )
    id: Mapped[uuid.UUID] = _uuid_pk()
    prodi_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("prodi.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    # NULL = panduan prodi (perilaku lama). Terisi = panduan pribadi pemilik.
    pemilik_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("orang.id", ondelete="RESTRICT"), index=True
    )
    versi: Mapped[int] = mapped_column(Integer, nullable=False)
    judul: Mapped[str] = mapped_column(String(300), nullable=False)
    berlaku_mulai: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="draf")
    berkas_nama: Mapped[str] = mapped_column(String(255), nullable=False)
    berkas_path: Mapped[str] = mapped_column(String(500), nullable=False)
    # Teks hasil ekstraksi PDF; dipakai layanan rekomendasi sebagai dasar aturan prodi.
    teks: Mapped[str | None] = mapped_column(Text)
    teks_karakter: Mapped[int | None] = mapped_column(Integer)
    dibuat_oleh: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("orang.id"))
    dibuat: Mapped[datetime] = _dibuat()


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    pelaku_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    aksi: Mapped[str] = mapped_column(String(64), nullable=False)
    objek_tipe: Mapped[str] = mapped_column(String(64), nullable=False)
    objek_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    sebelum: Mapped[dict | None] = mapped_column(JSONB)
    sesudah: Mapped[dict | None] = mapped_column(JSONB)
    waktu: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


STATUS_PENGAJUAN = ("diajukan", "disetujui", "ditolak", "revisi", "dibatalkan")


class Pengajuan(Base):
    """Rencana studi yang diajukan mahasiswa ke dosen pembimbing akademik (DPA)."""

    __tablename__ = "pengajuan"
    __table_args__ = (
        CheckConstraint(
            "status IN ('diajukan','disetujui','ditolak','revisi','dibatalkan')",
            name="ck_pengajuan_status",
        ),
        CheckConstraint("mode IN ('alurkerja','lokal')", name="ck_pengajuan_mode"),
        CheckConstraint("semester_target BETWEEN 1 AND 14", name="ck_pengajuan_semester"),
        CheckConstraint(
            "tahap IN ('ekstraksi','periksa','rekomendasi','tinjau','revisi','selesai')", name="ck_pengajuan_tahap"
        ),
        # Satu pengajuan terbuka per mahasiswa. Setelah diputuskan atau dibatalkan boleh mengajukan lagi.
        Index(
            "uq_pengajuan_terbuka",
            "mahasiswa_id",
            unique=True,
            postgresql_where=text("status = 'diajukan'"),
        ),
        Index("ix_pengajuan_status", "status"),
    )
    id: Mapped[uuid.UUID] = _uuid_pk()
    mahasiswa_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orang.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    dpa_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orang.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    prodi_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("prodi.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    panduan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("panduan_akademik.id", ondelete="RESTRICT"), nullable=False
    )
    panduan_versi: Mapped[int] = mapped_column(Integer, nullable=False)
    semester_target: Mapped[int] = mapped_column(Integer, nullable=False)
    ringkasan: Mapped[str | None] = mapped_column(Text)
    # Tidak dipakai lagi (dulu paket bertanda tangan). Dibiarkan agar migrasi tidak menghapus data.
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    khs_file_id: Mapped[str | None] = mapped_column(String(64))
    # Posisi proses: ekstraksi, periksa (menunggu mahasiswa), rekomendasi, tinjau (menunggu DPA), revisi, selesai.
    tahap: Mapped[str] = mapped_column(String(16), nullable=False, server_default="ekstraksi")
    # Hasil langkah proses (tanpa nama): ipk, sks_lulus, mk_ulang, keyakinan, rencana_mk, total_sks, peringatan, ...
    data_proses: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    pesan_galat: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="diajukan")
    catatan_dpa: Mapped[str | None] = mapped_column(Text)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    alurkerja_instance_id: Mapped[str | None] = mapped_column(String(64))
    diajukan_pada: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    diputuskan_pada: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PembimbingTA(Base):
    """Dosen pembimbing tugas akhir, ditunjuk kaprodi (terpisah dari dosen PA)."""

    __tablename__ = "pembimbing_ta"
    __table_args__ = (
        CheckConstraint("dosen_id <> mahasiswa_id", name="ck_pembimbing_ta_diri"),
        Index("uq_pembimbing_ta_aktif", "mahasiswa_id", unique=True, postgresql_where=text("selesai IS NULL")),
    )
    id: Mapped[uuid.UUID] = _uuid_pk()
    dosen_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orang.id", ondelete="RESTRICT"), nullable=False, index=True)
    mahasiswa_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orang.id", ondelete="RESTRICT"), nullable=False)
    mulai: Mapped[date] = mapped_column(Date, nullable=False)
    selesai: Mapped[date | None] = mapped_column(Date)
    dibuat: Mapped[datetime] = _dibuat()


class PengajuanJudul(Base):
    """Judul tugas akhir yang diajukan mahasiswa ke pembimbing TA."""

    __tablename__ = "pengajuan_judul"
    __table_args__ = (
        CheckConstraint("status IN ('diajukan','disetujui','dibatalkan')", name="ck_judul_status"),
        CheckConstraint("tahap IN ('tinjau','perbaikan','selesai')", name="ck_judul_tahap"),
        CheckConstraint("mode IN ('alurkerja','lokal')", name="ck_judul_mode"),
        Index("uq_judul_terbuka", "mahasiswa_id", unique=True, postgresql_where=text("status = 'diajukan'")),
    )
    id: Mapped[uuid.UUID] = _uuid_pk()
    mahasiswa_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orang.id", ondelete="RESTRICT"), nullable=False, index=True)
    pembimbing_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orang.id", ondelete="RESTRICT"), nullable=False, index=True)
    prodi_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("prodi.id", ondelete="RESTRICT"), nullable=False)
    topik: Mapped[str] = mapped_column(String(300), nullable=False, server_default="")
    judul: Mapped[str] = mapped_column(String(300), nullable=False)
    # Salah satu tema baku (src/domain/tema.py), untuk rekap per prodi.
    tema: Mapped[str] = mapped_column(String(80), nullable=False)
    deskripsi: Mapped[str] = mapped_column(Text, nullable=False)
    metodologi: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    keywords: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    referensi: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="diajukan")
    # tinjau (menunggu pembimbing), perbaikan (menunggu mahasiswa), selesai.
    tahap: Mapped[str] = mapped_column(String(16), nullable=False, server_default="tinjau")
    catatan: Mapped[str | None] = mapped_column(Text)
    jumlah_revisi: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    alurkerja_instance_id: Mapped[str | None] = mapped_column(String(64))
    diajukan_pada: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    diputuskan_pada: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RekomendasiJudul(Base):
    __tablename__ = "rekomendasi_judul"
    id: Mapped[uuid.UUID] = _uuid_pk()
    mahasiswa_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orang.id", ondelete="RESTRICT"), nullable=False)
    topik: Mapped[str] = mapped_column(String(300), nullable=False)
    hasil: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    dibuat: Mapped[datetime] = _dibuat()


class ObrolanJudul(Base):
    """Brainstorm judul milik satu mahasiswa: percakapan dan kandidat. Tidak berarti ada judul yang dipilih."""

    __tablename__ = "obrolan_judul"
    id: Mapped[uuid.UUID] = _uuid_pk()
    mahasiswa_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orang.id", ondelete="RESTRICT"), nullable=False)
    topik: Mapped[str] = mapped_column(String(300), nullable=False)
    pesan: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    kandidat: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    dibuat: Mapped[datetime] = _dibuat()
    diubah: Mapped[datetime] = _dibuat()


class AiPemakaian(Base):
    """Satu panggilan AI dari layanan mana pun. Isi prompt dan jawaban sengaja tidak disimpan."""

    __tablename__ = "ai_pemakaian"
    __table_args__ = (Index("ix_ai_pemakaian_waktu", "waktu"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    waktu: Mapped[datetime] = _dibuat()
    layanan: Mapped[str] = mapped_column(String(20), nullable=False)
    fitur: Mapped[str] = mapped_column(String(40), nullable=False)
    model: Mapped[str] = mapped_column(String(60), nullable=False)
    # Tanpa foreign key: catatan tetap ada walau akun berubah.
    akun_id: Mapped[uuid.UUID | None] = mapped_column()
    token_masuk: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    token_keluar: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    durasi_ms: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    berhasil: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
