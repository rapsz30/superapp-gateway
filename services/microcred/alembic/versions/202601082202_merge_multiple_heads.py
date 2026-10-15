"""merge multiple heads from 202501082201 and 202601080002

Revision ID: 202601082202
Revises: 202601080002, 202501082201
Create Date: 2026-01-08 22:02:00

This is a merge migration to resolve the multiple heads issue.
The old migration 202501082201 was incorrectly placed and has been replaced
with 202601082201, but production database may already have the old one applied.
"""

# revision identifiers, used by Alembic.
revision = "202601082202"
down_revision = ("202601080002", "202501082201")  # Merge both heads
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Merge migrations - no schema changes needed."""
    pass


def downgrade() -> None:
    """Downgrade is not supported for merge migrations."""
    pass
