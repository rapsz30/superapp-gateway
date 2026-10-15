"""Add recommendations tables

Revision ID: 202412300001
Revises: 202412250006
Create Date: 2025-12-30

Story 3.1 & 3.2: RAG Retrieval and Fusion Summary
- recommendations: Stores fusion narrative and overall recommendation
- recommendation_items: Individual recommended courses from RAG

Story 3.3: Feedback Collection
- feedbacks: Advisor/student feedback on recommendations
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "202412300001"
down_revision: str | None = "202412250006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Recommendations table
    op.create_table(
        "recommendations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "assessment_id",
            sa.String(36),
            sa.ForeignKey("assessments.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("summary", sa.Text, nullable=False),
        sa.Column("overall_score", sa.Float, nullable=False),
        sa.Column("degraded", sa.Boolean, default=False, nullable=False),
        sa.Column("rag_query", sa.Text, nullable=True),
        sa.Column("rag_traces", sa.JSON, nullable=True),
        sa.Column("score_breakdown", sa.JSON, nullable=True),
        sa.Column("processing_duration_ms", sa.Integer, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_recommendations_assessment_id", "recommendations", ["assessment_id"])

    # Recommendation items table
    op.create_table(
        "recommendation_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "recommendation_id",
            sa.String(36),
            sa.ForeignKey("recommendations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("rank", sa.Integer, nullable=False),
        sa.Column("course_id", sa.String(64), nullable=False),
        sa.Column("course_title", sa.String(512), nullable=False),
        sa.Column("course_url", sa.String(512), nullable=True),
        sa.Column("relevance_score", sa.Float, nullable=False),
        sa.Column("match_reason", sa.Text, nullable=True),
        sa.Column("course_metadata", sa.JSON, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_recommendation_items_recommendation_id",
        "recommendation_items",
        ["recommendation_id"],
    )

    # Feedbacks table
    op.create_table(
        "feedbacks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "recommendation_id",
            sa.String(36),
            sa.ForeignKey("recommendations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("user_role", sa.String(20), nullable=False),
        sa.Column("rating_relevance", sa.Integer, nullable=True),
        sa.Column("rating_acceptance", sa.Integer, nullable=True),
        sa.Column("comment", sa.Text, nullable=True),
        sa.Column("track_slug", sa.String(64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_feedbacks_recommendation_id", "feedbacks", ["recommendation_id"])
    op.create_index("ix_feedbacks_user_id", "feedbacks", ["user_id"])


def downgrade() -> None:
    op.drop_table("feedbacks")
    op.drop_table("recommendation_items")
    op.drop_table("recommendations")
