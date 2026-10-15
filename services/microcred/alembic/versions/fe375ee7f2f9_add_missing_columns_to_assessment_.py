"""add_missing_columns_to_assessment_question_snapshots

Revision ID: fe375ee7f2f9
Revises: 202601090003
Create Date: 2026-02-09 23:56:42.772741
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "fe375ee7f2f9"
down_revision = "202601090003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add missing columns to assessment_question_snapshots table"""

    # Add difficulty column
    op.add_column(
        "assessment_question_snapshots", sa.Column("difficulty", sa.String(), nullable=True)
    )

    # Add weight column with default 1.0
    op.add_column(
        "assessment_question_snapshots",
        sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
    )

    # Add correct_answer column
    op.add_column(
        "assessment_question_snapshots", sa.Column("correct_answer", sa.String(), nullable=True)
    )

    # Add answer_key column
    op.add_column(
        "assessment_question_snapshots", sa.Column("answer_key", sa.Text(), nullable=True)
    )

    # Add model_answer column
    op.add_column(
        "assessment_question_snapshots", sa.Column("model_answer", sa.Text(), nullable=True)
    )

    # Add rubric column (JSON)
    op.add_column(
        "assessment_question_snapshots",
        sa.Column("rubric", postgresql.JSON(astext_type=sa.Text()), nullable=True),
    )

    # Add expected_values column (JSON)
    op.add_column(
        "assessment_question_snapshots",
        sa.Column("expected_values", postgresql.JSON(astext_type=sa.Text()), nullable=True),
    )

    # Rename metadata to metadata_ to match model
    op.alter_column("assessment_question_snapshots", "metadata", new_column_name="metadata_")


def downgrade() -> None:
    """Remove columns added in upgrade"""

    # Rename metadata_ back to metadata
    op.alter_column("assessment_question_snapshots", "metadata_", new_column_name="metadata")

    # Drop columns in reverse order
    op.drop_column("assessment_question_snapshots", "expected_values")
    op.drop_column("assessment_question_snapshots", "rubric")
    op.drop_column("assessment_question_snapshots", "model_answer")
    op.drop_column("assessment_question_snapshots", "answer_key")
    op.drop_column("assessment_question_snapshots", "correct_answer")
    op.drop_column("assessment_question_snapshots", "weight")
    op.drop_column("assessment_question_snapshots", "difficulty")
