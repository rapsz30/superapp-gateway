"""Skema awal identity: struktur organisasi, akun, penugasan, bimbingan, panduan, audit.

Revision ID: 0001
Revises:
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def _id():
    return sa.Column(
        "id", pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    )


def _dibuat():
    return sa.Column(
        "dibuat", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )


def _fk(nama, target, ondelete=None, nullable=False, unique=False):
    return sa.Column(
        nama,
        pg.UUID(as_uuid=True),
        sa.ForeignKey(target, ondelete=ondelete),
        nullable=nullable,
        unique=unique,
    )


def upgrade() -> None:
    op.create_table(
        "fakultas",
        _id(),
        sa.Column("kode", sa.String(32), nullable=False, unique=True),
        sa.Column("nama", sa.String(200), nullable=False),
        sa.Column("aktif", sa.Boolean, nullable=False, server_default=sa.text("true")),
        _dibuat(),
    )
    op.create_table(
        "jurusan",
        _id(),
        _fk("fakultas_id", "fakultas.id", "RESTRICT"),
        sa.Column("kode", sa.String(32), nullable=False),
        sa.Column("nama", sa.String(200), nullable=False),
        sa.Column("aktif", sa.Boolean, nullable=False, server_default=sa.text("true")),
        _dibuat(),
        sa.UniqueConstraint("fakultas_id", "kode", name="uq_jurusan_kode"),
    )
    op.create_index("ix_jurusan_fakultas_id", "jurusan", ["fakultas_id"])
    op.create_table(
        "prodi",
        _id(),
        _fk("jurusan_id", "jurusan.id", "RESTRICT"),
        sa.Column("kode", sa.String(32), nullable=False),
        sa.Column("nama", sa.String(200), nullable=False),
        sa.Column("jenjang", sa.String(16), nullable=False, server_default="S1"),
        sa.Column("aktif", sa.Boolean, nullable=False, server_default=sa.text("true")),
        _dibuat(),
        sa.UniqueConstraint("jurusan_id", "kode", name="uq_prodi_kode"),
        sa.CheckConstraint("jenjang IN ('D3','S1','S2','S3','Profesi')", name="ck_prodi_jenjang"),
    )
    op.create_index("ix_prodi_jurusan_id", "prodi", ["jurusan_id"])

    op.create_table(
        "orang",
        _id(),
        sa.Column("nama_lengkap", sa.String(200), nullable=False),
        sa.Column("nim", sa.String(32), unique=True),
        sa.Column("nidn", sa.String(32), unique=True),
        sa.Column("email_kontak", sa.String(255)),
        _dibuat(),
    )
    op.create_table(
        "akun",
        _id(),
        _fk("orang_id", "orang.id", "RESTRICT", unique=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("sandi_hash", sa.String(255), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="aktif"),
        sa.Column("wajib_ganti_sandi", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("versi_token", sa.Integer, nullable=False, server_default=sa.text("1")),
        sa.Column("login_terakhir", sa.DateTime(timezone=True)),
        _dibuat(),
        sa.CheckConstraint("status IN ('aktif','ditangguhkan','nonaktif')", name="ck_akun_status"),
    )
    op.create_index("uq_akun_email_lower", "akun", [sa.text("lower(email)")], unique=True)
    op.create_table(
        "refresh_token",
        _id(),
        _fk("akun_id", "akun.id", "CASCADE"),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("kedaluwarsa", sa.DateTime(timezone=True), nullable=False),
        sa.Column("dicabut", sa.DateTime(timezone=True)),
        _dibuat(),
    )
    op.create_index("ix_refresh_token_akun_id", "refresh_token", ["akun_id"])

    op.create_table(
        "penugasan",
        _id(),
        _fk("orang_id", "orang.id", "RESTRICT"),
        sa.Column("peran", sa.String(16), nullable=False),
        sa.Column("unit_tipe", sa.String(16), nullable=False),
        sa.Column("unit_id", pg.UUID(as_uuid=True)),
        sa.Column("mulai", sa.Date, nullable=False),
        sa.Column("selesai", sa.Date),
        _fk("dibuat_oleh", "orang.id", nullable=True),
        _dibuat(),
        sa.CheckConstraint(
            "peran IN ('superadmin','dekan','kajur','kaprodi','dosen_pa')", name="ck_penugasan_peran"
        ),
        sa.CheckConstraint(
            "unit_tipe IN ('global','fakultas','jurusan','prodi')", name="ck_penugasan_unit_tipe"
        ),
        sa.CheckConstraint("(unit_tipe = 'global') = (unit_id IS NULL)", name="ck_penugasan_unit_id"),
        sa.CheckConstraint(
            "(peran = 'superadmin' AND unit_tipe = 'global')"
            " OR (peran = 'dekan' AND unit_tipe = 'fakultas')"
            " OR (peran = 'kajur' AND unit_tipe = 'jurusan')"
            " OR (peran = 'kaprodi' AND unit_tipe = 'prodi')"
            " OR (peran = 'dosen_pa' AND unit_tipe IN ('prodi','jurusan'))",
            name="ck_penugasan_peran_unit",
        ),
        sa.CheckConstraint("selesai IS NULL OR selesai >= mulai", name="ck_penugasan_tanggal"),
    )
    op.create_index("ix_penugasan_orang_id", "penugasan", ["orang_id"])
    op.create_index("ix_penugasan_unit_id", "penugasan", ["unit_id"])
    for nama, peran in (("uq_dekan_aktif", "dekan"), ("uq_kajur_aktif", "kajur"), ("uq_kaprodi_aktif", "kaprodi")):
        op.create_index(
            nama,
            "penugasan",
            ["unit_id"],
            unique=True,
            postgresql_where=sa.text(f"peran = '{peran}' AND selesai IS NULL"),
        )
    op.create_index(
        "uq_penugasan_orang_unit_aktif",
        "penugasan",
        ["orang_id", "peran", "unit_id"],
        unique=True,
        postgresql_where=sa.text("selesai IS NULL AND unit_id IS NOT NULL"),
    )

    op.create_table(
        "keanggotaan_prodi",
        _id(),
        _fk("orang_id", "orang.id", "RESTRICT"),
        _fk("prodi_id", "prodi.id", "RESTRICT"),
        sa.Column("angkatan", sa.Integer),
        sa.Column("status", sa.String(16), nullable=False, server_default="aktif"),
        sa.Column("mulai", sa.Date, nullable=False),
        sa.Column("selesai", sa.Date),
        _dibuat(),
        sa.CheckConstraint(
            "status IN ('aktif','cuti','lulus','keluar','pindah')", name="ck_keanggotaan_status"
        ),
        sa.CheckConstraint("selesai IS NULL OR selesai >= mulai", name="ck_keanggotaan_tanggal"),
        sa.CheckConstraint(
            "(selesai IS NULL) = (status IN ('aktif','cuti'))", name="ck_keanggotaan_status_selesai"
        ),
    )
    op.create_index("ix_keanggotaan_prodi_orang_id", "keanggotaan_prodi", ["orang_id"])
    op.create_index("ix_keanggotaan_prodi_prodi_id", "keanggotaan_prodi", ["prodi_id"])
    op.create_index(
        "uq_keanggotaan_aktif",
        "keanggotaan_prodi",
        ["orang_id"],
        unique=True,
        postgresql_where=sa.text("selesai IS NULL"),
    )

    op.create_table(
        "bimbingan",
        _id(),
        _fk("dosen_id", "orang.id", "RESTRICT"),
        _fk("mahasiswa_id", "orang.id", "RESTRICT"),
        sa.Column("mulai", sa.Date, nullable=False),
        sa.Column("selesai", sa.Date),
        _dibuat(),
        sa.CheckConstraint("dosen_id <> mahasiswa_id", name="ck_bimbingan_diri"),
        sa.CheckConstraint("selesai IS NULL OR selesai >= mulai", name="ck_bimbingan_tanggal"),
    )
    op.create_index("ix_bimbingan_dosen_id", "bimbingan", ["dosen_id"])
    op.create_index("ix_bimbingan_mahasiswa_id", "bimbingan", ["mahasiswa_id"])
    op.create_index(
        "uq_bimbingan_aktif",
        "bimbingan",
        ["mahasiswa_id"],
        unique=True,
        postgresql_where=sa.text("selesai IS NULL"),
    )

    op.create_table(
        "panduan_akademik",
        _id(),
        _fk("prodi_id", "prodi.id", "RESTRICT"),
        sa.Column("versi", sa.Integer, nullable=False),
        sa.Column("judul", sa.String(300), nullable=False),
        sa.Column("berlaku_mulai", sa.Date),
        sa.Column("status", sa.String(16), nullable=False, server_default="draf"),
        sa.Column("berkas_nama", sa.String(255), nullable=False),
        sa.Column("berkas_path", sa.String(500), nullable=False),
        _fk("dibuat_oleh", "orang.id", nullable=True),
        _dibuat(),
        sa.UniqueConstraint("prodi_id", "versi", name="uq_panduan_versi"),
        sa.CheckConstraint("status IN ('draf','aktif','diarsipkan')", name="ck_panduan_status"),
    )
    op.create_index("ix_panduan_akademik_prodi_id", "panduan_akademik", ["prodi_id"])
    op.create_index(
        "uq_panduan_aktif",
        "panduan_akademik",
        ["prodi_id"],
        unique=True,
        postgresql_where=sa.text("status = 'aktif'"),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("pelaku_id", pg.UUID(as_uuid=True)),
        sa.Column("aksi", sa.String(64), nullable=False),
        sa.Column("objek_tipe", sa.String(64), nullable=False),
        sa.Column("objek_id", pg.UUID(as_uuid=True)),
        sa.Column("sebelum", pg.JSONB),
        sa.Column("sesudah", pg.JSONB),
        sa.Column("waktu", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_log_pelaku_id", "audit_log", ["pelaku_id"])
    op.create_index("ix_audit_log_objek_id", "audit_log", ["objek_id"])

    # Audit hanya-tambah: ubah atau hapus ditolak oleh database.
    op.execute(
        """
        CREATE FUNCTION audit_log_tolak_ubah() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'audit_log bersifat hanya-tambah';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        "CREATE TRIGGER audit_log_hanya_tambah BEFORE UPDATE OR DELETE ON audit_log "
        "FOR EACH ROW EXECUTE FUNCTION audit_log_tolak_ubah()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_log_hanya_tambah ON audit_log")
    op.execute("DROP FUNCTION IF EXISTS audit_log_tolak_ubah()")
    for tabel in (
        "audit_log",
        "panduan_akademik",
        "bimbingan",
        "keanggotaan_prodi",
        "penugasan",
        "refresh_token",
        "akun",
        "orang",
        "prodi",
        "jurusan",
        "fakultas",
    ):
        op.drop_table(tabel)
