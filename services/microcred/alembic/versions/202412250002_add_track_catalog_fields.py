"""add track catalog fields for story 1.2

Revision ID: 202412250002
Revises: 202412250001
Create Date: 2025-12-25 05:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "202412250002"
down_revision: str | None = "202412250001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add new columns to role_catalog table
    op.add_column(
        "role_catalog",
        sa.Column("skill_focus_tags", postgresql.JSON(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "role_catalog",
        sa.Column("question_mix_overrides", postgresql.JSON(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "role_catalog",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.add_column(
        "role_catalog",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.add_column(
        "role_catalog",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # Update existing records with skill focus tags and question mix
    op.execute("""
        UPDATE role_catalog
        SET skill_focus_tags = '["backend", "api-design", "databases"]'::json,
            question_mix_overrides = '{"theoretical": 4, "essay": 4, "profile": 2}'::json
        WHERE slug = 'backend-engineer'
    """)

    op.execute("""
        UPDATE role_catalog
        SET skill_focus_tags = '["data-analysis", "sql", "visualization"]'::json,
            question_mix_overrides = '{"theoretical": 3, "essay": 5, "profile": 2}'::json
        WHERE slug = 'data-analyst'
    """)


def downgrade() -> None:
    op.drop_column("role_catalog", "updated_at")
    op.drop_column("role_catalog", "created_at")
    op.drop_column("role_catalog", "is_active")
    op.drop_column("role_catalog", "question_mix_overrides")
    op.drop_column("role_catalog", "skill_focus_tags")
