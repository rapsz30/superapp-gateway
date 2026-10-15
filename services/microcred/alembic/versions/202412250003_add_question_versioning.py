"""add_question_versioning

Revision ID: 202412250003
Revises: 202412250002
Create Date: 2025-12-25 05:23:52.950572
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "202412250003"
down_revision = "202412250002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add versioning and soft delete columns to question_templates
    op.add_column(
        "question_templates", sa.Column("version", sa.Integer(), nullable=False, server_default="1")
    )
    op.add_column(
        "question_templates", sa.Column("previous_version_id", sa.Integer(), nullable=True)
    )
    op.add_column(
        "question_templates",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.add_column(
        "question_templates",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.add_column(
        "question_templates",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )


def downgrade() -> None:
    # Remove versioning columns
    op.drop_column("question_templates", "updated_at")
    op.drop_column("question_templates", "created_at")
    op.drop_column("question_templates", "is_active")
    op.drop_column("question_templates", "previous_version_id")
    op.drop_column("question_templates", "version")
