"""Add student identity columns (nim, faculty, study_program) to users

Revision ID: 202610240001
Revises: 202602170001
Create Date: 2026-10-24 00:01:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "202610240001"
down_revision = "202602170001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Kolom nullable agar akun lama tidak rusak
    op.add_column("users", sa.Column("nim", sa.String(length=32), nullable=True))
    op.add_column("users", sa.Column("faculty", sa.String(length=100), nullable=True))
    op.add_column("users", sa.Column("study_program", sa.String(length=100), nullable=True))
    # Index unik: menjadi pengaman NIM duplikat saat permintaan bersamaan
    op.create_index("ix_users_nim", "users", ["nim"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_nim", table_name="users")
    op.drop_column("users", "study_program")
    op.drop_column("users", "faculty")
    op.drop_column("users", "nim")

