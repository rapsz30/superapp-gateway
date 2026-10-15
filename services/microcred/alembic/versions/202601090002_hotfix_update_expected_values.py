"""hotfix update expected values for Q8 Q9 Q10

Revision ID: 202601090002
Revises: 202601090001
Create Date: 2026-01-09 00:50:50.598966
"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "202601090002"
down_revision = "202601090001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Hotfix: Update only expected_values for Q8-Q10."""
    # Update Q8 expected_values only
    op.execute(
        "UPDATE question_templates "
        'SET expected_values = \'{"accepted_values": ["docker", "kubernetes", "aws", '
        '"gcp", "azure", "graphql", "redis", "kafka", "microservices", "ci/cd", '
        '"terraform", "mongodb", "postgresql", "elasticsearch"], "allow_custom": true}\'::json '
        "WHERE role_slug = 'backend-engineer' AND sequence = 8 AND question_type = 'profile';"
    )

    # Update Q9 expected_values only
    op.execute(
        "UPDATE question_templates "
        'SET expected_values = \'{"accepted_values": ["short", "medium", "long", "any"]}\'::json '
        "WHERE role_slug = 'backend-engineer' AND sequence = 9 AND question_type = 'profile';"
    )

    # Update Q10 expected_values only
    op.execute(
        "UPDATE question_templates "
        'SET expected_values = \'{"accepted_values": ["paid", "free", "any"]}\'::json '
        "WHERE role_slug = 'backend-engineer' AND sequence = 10 AND question_type = 'profile';"
    )


def downgrade() -> None:
    """No downgrade needed - expected_values fix is permanent."""
    pass
