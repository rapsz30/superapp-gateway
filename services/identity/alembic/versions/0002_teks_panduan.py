"""Simpan teks hasil ekstraksi panduan akademik.

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Nullable karena baris lama (bila ada) belum punya teks.
    op.add_column("panduan_akademik", sa.Column("teks", sa.Text(), nullable=True))
    op.add_column("panduan_akademik", sa.Column("teks_karakter", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("panduan_akademik", "teks_karakter")
    op.drop_column("panduan_akademik", "teks")
