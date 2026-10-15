"""Add webhook_url and idempotency_key to assessments

Revision ID: 202412250006
Revises: 202412250005
Create Date: 2025-12-30

Story 2.3: Status Polling, Webhooks, and Idempotency
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "202412250006"
down_revision = "202412250005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add webhook_url column
    op.add_column(
        "assessments",
        sa.Column("webhook_url", sa.String(512), nullable=True),
    )

    # Add idempotency_key column with unique constraint
    op.add_column(
        "assessments",
        sa.Column("idempotency_key", sa.String(64), nullable=True),
    )

    # Create unique index for idempotency_key
    op.create_index(
        "ix_assessments_idempotency_key",
        "assessments",
        ["idempotency_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_assessments_idempotency_key", table_name="assessments")
    op.drop_column("assessments", "idempotency_key")
    op.drop_column("assessments", "webhook_url")
