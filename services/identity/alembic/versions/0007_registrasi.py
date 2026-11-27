"""Registrasi publik: isian prodi/PT pada orang, panduan pribadi.

Revision ID: 0007
Revises: 0006
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orang", sa.Column("prodi_isian", sa.String(200)))
    op.add_column("orang", sa.Column("pt_isian", sa.String(200)))

    op.add_column(
        "panduan_akademik",
        sa.Column("pemilik_id", pg.UUID(as_uuid=True), sa.ForeignKey("orang.id", ondelete="RESTRICT")),
    )
    op.create_index("ix_panduan_akademik_pemilik_id", "panduan_akademik", ["pemilik_id"])

    op.drop_index("uq_panduan_aktif", table_name="panduan_akademik")
    op.create_index(
        "uq_panduan_aktif",
        "panduan_akademik",
        ["prodi_id"],
        unique=True,
        postgresql_where=sa.text("status = 'aktif' AND pemilik_id IS NULL"),
    )
    op.create_index(
        "uq_panduan_aktif_pemilik",
        "panduan_akademik",
        ["pemilik_id"],
        unique=True,
        postgresql_where=sa.text("status = 'aktif' AND pemilik_id IS NOT NULL"),
    )

    op.drop_constraint("uq_panduan_versi", "panduan_akademik", type_="unique")
    op.create_index(
        "uq_panduan_versi",
        "panduan_akademik",
        ["prodi_id", "versi"],
        unique=True,
        postgresql_where=sa.text("pemilik_id IS NULL"),
    )
    op.create_index(
        "uq_panduan_versi_pemilik",
        "panduan_akademik",
        ["pemilik_id", "versi"],
        unique=True,
        postgresql_where=sa.text("pemilik_id IS NOT NULL"),
    )


def downgrade() -> None:
    # Panduan pribadi harus dihapus dulu; indeks versi prodi lama tidak mencakup baris dengan pemilik.
    op.execute("DELETE FROM panduan_akademik WHERE pemilik_id IS NOT NULL")

    op.drop_index("uq_panduan_versi_pemilik", table_name="panduan_akademik")
    op.drop_index("uq_panduan_versi", table_name="panduan_akademik")
    op.create_unique_constraint("uq_panduan_versi", "panduan_akademik", ["prodi_id", "versi"])

    op.drop_index("uq_panduan_aktif_pemilik", table_name="panduan_akademik")
    op.drop_index("uq_panduan_aktif", table_name="panduan_akademik")
    op.create_index(
        "uq_panduan_aktif",
        "panduan_akademik",
        ["prodi_id"],
        unique=True,
        postgresql_where=sa.text("status = 'aktif'"),
    )

    op.drop_index("ix_panduan_akademik_pemilik_id", table_name="panduan_akademik")
    op.drop_column("panduan_akademik", "pemilik_id")
    op.drop_column("orang", "pt_isian")
    op.drop_column("orang", "prodi_isian")
