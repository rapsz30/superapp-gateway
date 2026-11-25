"""Pengajuan rencana studi ke dosen pembimbing akademik.

Revision ID: 0003
Revises: 0002
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pengajuan",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("mahasiswa_id", pg.UUID(as_uuid=True), sa.ForeignKey("orang.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("dpa_id", pg.UUID(as_uuid=True), sa.ForeignKey("orang.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("prodi_id", pg.UUID(as_uuid=True), sa.ForeignKey("prodi.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("panduan_id", pg.UUID(as_uuid=True), sa.ForeignKey("panduan_akademik.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("panduan_versi", sa.Integer, nullable=False),
        sa.Column("semester_target", sa.Integer, nullable=False),
        sa.Column("ringkasan", sa.Text),
        sa.Column("payload", pg.JSONB, nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="diajukan"),
        sa.Column("catatan_dpa", sa.Text),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("alurkerja_instance_id", sa.String(64)),
        sa.Column("diajukan_pada", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("diputuskan_pada", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "status IN ('diajukan','disetujui','ditolak','revisi','dibatalkan')", name="ck_pengajuan_status"
        ),
        sa.CheckConstraint("mode IN ('alurkerja','lokal')", name="ck_pengajuan_mode"),
        sa.CheckConstraint("semester_target BETWEEN 1 AND 14", name="ck_pengajuan_semester"),
    )
    op.create_index("ix_pengajuan_mahasiswa_id", "pengajuan", ["mahasiswa_id"])
    op.create_index("ix_pengajuan_dpa_id", "pengajuan", ["dpa_id"])
    op.create_index("ix_pengajuan_prodi_id", "pengajuan", ["prodi_id"])
    op.create_index("ix_pengajuan_status", "pengajuan", ["status"])
    op.create_index(
        "uq_pengajuan_terbuka",
        "pengajuan",
        ["mahasiswa_id"],
        unique=True,
        postgresql_where=sa.text("status = 'diajukan'"),
    )


def downgrade() -> None:
    op.drop_table("pengajuan")
