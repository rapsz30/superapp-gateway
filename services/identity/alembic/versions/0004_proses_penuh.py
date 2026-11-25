"""Pengajuan menjalankan proses AlurKerja lengkap; batas SKS per prodi.

Revision ID: 0004
Revises: 0003
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("prodi", sa.Column("maks_sks_semester", sa.Integer(), nullable=True))
    op.create_check_constraint(
        "ck_prodi_maks_sks", "prodi", "maks_sks_semester IS NULL OR maks_sks_semester BETWEEN 1 AND 40"
    )

    op.add_column("pengajuan", sa.Column("khs_file_id", sa.String(64)))
    op.add_column("pengajuan", sa.Column("tahap", sa.String(16), nullable=False, server_default="ekstraksi"))
    op.add_column(
        "pengajuan",
        sa.Column("data_proses", pg.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.add_column("pengajuan", sa.Column("pesan_galat", sa.Text()))
    op.create_check_constraint(
        "ck_pengajuan_tahap",
        "pengajuan",
        "tahap IN ('ekstraksi','periksa','rekomendasi','tinjau','revisi','selesai')",
    )
    # payload lama (paket bertanda tangan) tidak dipakai lagi.
    op.alter_column("pengajuan", "payload", nullable=False, server_default=sa.text("'{}'::jsonb"))


def downgrade() -> None:
    op.alter_column("pengajuan", "payload", server_default=None)
    op.drop_constraint("ck_pengajuan_tahap", "pengajuan")
    for kolom in ("pesan_galat", "data_proses", "tahap", "khs_file_id"):
        op.drop_column("pengajuan", kolom)
    op.drop_constraint("ck_prodi_maks_sks", "prodi")
    op.drop_column("prodi", "maks_sks_semester")
