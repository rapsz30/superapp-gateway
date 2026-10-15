"""update profile questions for personalized recommendations

Revision ID: 202601082201
Revises: 202601082202
Create Date: 2026-01-08 22:01:00

Updates profile questions Q2-Q4 to capture user preferences for personalization:
- Q2 (Seq 8): Technology preferences with allow_custom=True (user can input custom tech)
- Q3 (Seq 9): Content duration preference (short/medium/long/any)
- Q4 (Seq 10): Payment preference (paid/free/any)

These preferences are used by RAG service to:
1. Filter courses by payment preference
2. Boost courses matching user's tech preferences
3. Boost courses matching duration preference
4. Make recommendations deterministic (sort by course_id when scores equal)
"""

# revision identifiers, used by Alembic.
revision = "202601082201"
down_revision = "202601082202"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Update profile questions with personalization fields."""
    # Note: Questions are defined in reference_data.py and loaded at runtime
    # This migration is a marker for documentation purposes
    # The actual question updates are in the code changes to:
    # - reference_data.py: Q2-Q4 questions updated
    # - rag.py: Uses profile_signals for personalization
    pass


def downgrade() -> None:
    """Revert profile questions to original form."""
    pass
