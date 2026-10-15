"""add configurable advanced threshold to role catalog

Revision ID: 202602150001
Revises: 202602140001
Create Date: 2026-02-15 10:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "202602150001"
down_revision: str | None = "202602140001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "role_catalog",
        sa.Column("advanced_threshold_pct", sa.Float(), nullable=False, server_default="70.0"),
    )
    op.execute(
        """
        UPDATE role_catalog
        SET advanced_threshold_pct = 70.0
        WHERE advanced_threshold_pct IS NULL
        """
    )


def downgrade() -> None:
    op.drop_column("role_catalog", "advanced_threshold_pct")
