"""Judul tugas akhir: pembimbing TA, pengajuan judul, dan riwayat rekomendasi.

Revision ID: 0005
Revises: 0004
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def _id():
    return sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))


def _orang(nama: str):
    return sa.Column(nama, pg.UUID(as_uuid=True), sa.ForeignKey("orang.id", ondelete="RESTRICT"), nullable=False)


def _waktu(nama: str):
    return sa.Column(nama, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def _json(nama: str, bawaan: str):
    return sa.Column(nama, pg.JSONB, nullable=False, server_default=sa.text(f"'{bawaan}'::jsonb"))


def upgrade() -> None:
    op.create_table(
        "pembimbing_ta",
        _id(),
        _orang("dosen_id"),
        _orang("mahasiswa_id"),
        sa.Column("mulai", sa.Date(), nullable=False),
        sa.Column("selesai", sa.Date()),
        _waktu("dibuat"),
        sa.CheckConstraint("dosen_id <> mahasiswa_id", name="ck_pembimbing_ta_diri"),
    )
    op.create_index("ix_pembimbing_ta_dosen", "pembimbing_ta", ["dosen_id"])
    op.create_index(
        "uq_pembimbing_ta_aktif", "pembimbing_ta", ["mahasiswa_id"], unique=True,
        postgresql_where=sa.text("selesai IS NULL"),
    )

    op.create_table(
        "pengajuan_judul",
        _id(),
        _orang("mahasiswa_id"),
        _orang("pembimbing_id"),
        sa.Column("prodi_id", pg.UUID(as_uuid=True), sa.ForeignKey("prodi.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("topik", sa.String(300), nullable=False, server_default=""),
        sa.Column("judul", sa.String(300), nullable=False),
        sa.Column("tema", sa.String(80), nullable=False),
        sa.Column("deskripsi", sa.Text(), nullable=False),
        sa.Column("metodologi", sa.Text(), nullable=False, server_default=""),
        _json("keywords", "[]"),
        _json("referensi", "[]"),
        sa.Column("status", sa.String(16), nullable=False, server_default="diajukan"),
        sa.Column("tahap", sa.String(16), nullable=False, server_default="tinjau"),
        sa.Column("catatan", sa.Text()),
        sa.Column("jumlah_revisi", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("alurkerja_instance_id", sa.String(64)),
        _waktu("diajukan_pada"),
        sa.Column("diputuskan_pada", sa.DateTime(timezone=True)),
        sa.CheckConstraint("status IN ('diajukan','disetujui','dibatalkan')", name="ck_judul_status"),
        sa.CheckConstraint("tahap IN ('tinjau','perbaikan','selesai')", name="ck_judul_tahap"),
        sa.CheckConstraint("mode IN ('alurkerja','lokal')", name="ck_judul_mode"),
    )
    op.create_index("ix_judul_mahasiswa", "pengajuan_judul", ["mahasiswa_id"])
    op.create_index("ix_judul_prodi_tema", "pengajuan_judul", ["prodi_id", "tema"])
    op.create_index("ix_judul_pembimbing", "pengajuan_judul", ["pembimbing_id"])
    op.create_index(
        "uq_judul_terbuka", "pengajuan_judul", ["mahasiswa_id"], unique=True,
        postgresql_where=sa.text("status = 'diajukan'"),
    )

    op.create_table(
        "rekomendasi_judul",
        _id(),
        _orang("mahasiswa_id"),
        sa.Column("topik", sa.String(300), nullable=False),
        _json("hasil", "[]"),
        _waktu("dibuat"),
    )
    op.create_index("ix_rekomendasi_judul_mahasiswa", "rekomendasi_judul", ["mahasiswa_id", "dibuat"])


def downgrade() -> None:
    op.drop_table("rekomendasi_judul")
    op.drop_table("pengajuan_judul")
    op.drop_table("pembimbing_ta")
