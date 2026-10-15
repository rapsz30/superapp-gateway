"""add_assessment_expiry

Revision ID: 202412250004
Revises: 202412250003
Create Date: 2025-12-25 10:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "202412250004"
down_revision = "202412250003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add expires_at column to assessments table
    op.add_column(
        "assessments",
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("assessments", "expires_at")
