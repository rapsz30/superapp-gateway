"""Catatan pemakaian AI.

Revision ID: 0008
Revises: 0007
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_pemakaian",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("waktu", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("layanan", sa.String(20), nullable=False),
        sa.Column("fitur", sa.String(40), nullable=False),
        sa.Column("model", sa.String(60), nullable=False),
        sa.Column("akun_id", pg.UUID(as_uuid=True)),
        sa.Column("token_masuk", sa.Integer(), server_default="0", nullable=False),
        sa.Column("token_keluar", sa.Integer(), server_default="0", nullable=False),
        sa.Column("durasi_ms", sa.Integer(), server_default="0", nullable=False),
        sa.Column("berhasil", sa.Boolean(), server_default=sa.text("true"), nullable=False),
    )
    op.create_index("ix_ai_pemakaian_waktu", "ai_pemakaian", ["waktu"])


def downgrade() -> None:
    op.drop_table("ai_pemakaian")
