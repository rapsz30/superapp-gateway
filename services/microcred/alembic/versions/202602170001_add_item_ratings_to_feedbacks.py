"""add per-course item ratings to feedbacks

Revision ID: 202602170001
Revises: 202602150001
Create Date: 2026-02-17 23:30:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "202602170001"
down_revision: str | None = "202602150001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("feedbacks", sa.Column("item_ratings", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("feedbacks", "item_ratings")
