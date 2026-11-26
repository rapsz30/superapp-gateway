"""Brainstorm judul tugas akhir: percakapan dan kandidat per mahasiswa.

Revision ID: 0006
Revises: 0005
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "obrolan_judul",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("mahasiswa_id", pg.UUID(as_uuid=True), sa.ForeignKey("orang.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("topik", sa.String(300), nullable=False),
        sa.Column("pesan", pg.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("kandidat", pg.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("dibuat", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("diubah", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_obrolan_judul_mahasiswa", "obrolan_judul", ["mahasiswa_id", "diubah"])


def downgrade() -> None:
    op.drop_table("obrolan_judul")
