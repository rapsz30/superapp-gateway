"""fix profile question count

Revision ID: 202601080002
Revises: 202601080001
Create Date: 2026-01-08 16:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "202601080002"
down_revision = "202601080001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Update question_mix_overrides to use 4 profile questions instead of 2."""
    op.execute("""
        UPDATE role_catalog
        SET question_mix_overrides = '{"theoretical": 3, "essay": 3, "profile": 4}'::json
        WHERE slug = 'backend-engineer'
    """)

    op.execute("""
        UPDATE role_catalog
        SET question_mix_overrides = '{"theoretical": 3, "essay": 3, "profile": 4}'::json
        WHERE slug = 'data-analyst'
    """)


def downgrade() -> None:
    """Revert to 2 profile questions."""
    op.execute("""
        UPDATE role_catalog
        SET question_mix_overrides = '{"theoretical": 4, "essay": 4, "profile": 2}'::json
        WHERE slug = 'backend-engineer'
    """)

    op.execute("""
        UPDATE role_catalog
        SET question_mix_overrides = '{"theoretical": 3, "essay": 5, "profile": 2}'::json
        WHERE slug = 'data-analyst'
    """)
