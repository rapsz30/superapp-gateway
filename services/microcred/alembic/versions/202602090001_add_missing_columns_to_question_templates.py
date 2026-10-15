"""add missing columns to question_templates

Revision ID: 202602090001
Revises: 202601090003
Create Date: 2026-02-09 21:50:00

Adds missing columns to question_templates that exist in the model but not in schema:
- difficulty (String): Question difficulty level
- weight (Float): Score weight multiplier
- correct_answer (String): Correct answer for multiple choice
- answer_key (Text): Reference answer for essays
- model_answer (Text): Model/example answer
- rubric (JSON): Scoring rubric for GPT
- expected_values (JSON): Expected values for profile questions
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "202602090001"
down_revision: str | None = "202601082201"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add missing columns to question_templates table."""
    # Add difficulty column
    op.add_column(
        "question_templates",
        sa.Column("difficulty", sa.String(length=32), nullable=True, server_default="medium"),
    )

    # Add weight column for scoring
    op.add_column(
        "question_templates",
        sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
    )

    # Add correct_answer for multiple choice questions
    op.add_column(
        "question_templates",
        sa.Column("correct_answer", sa.String(length=255), nullable=True),
    )

    # Add answer_key for reference answers
    op.add_column(
        "question_templates",
        sa.Column("answer_key", sa.Text(), nullable=True),
    )

    # Add model_answer for example answers
    op.add_column(
        "question_templates",
        sa.Column("model_answer", sa.Text(), nullable=True),
    )

    # Add rubric for GPT scoring
    op.add_column(
        "question_templates",
        sa.Column("rubric", postgresql.JSON(astext_type=sa.Text()), nullable=True),
    )

    # Add expected_values for profile questions
    op.add_column(
        "question_templates",
        sa.Column("expected_values", postgresql.JSON(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    """Remove added columns from question_templates table."""
    op.drop_column("question_templates", "expected_values")
    op.drop_column("question_templates", "rubric")
    op.drop_column("question_templates", "model_answer")
    op.drop_column("question_templates", "answer_key")
    op.drop_column("question_templates", "correct_answer")
    op.drop_column("question_templates", "weight")
    op.drop_column("question_templates", "difficulty")
