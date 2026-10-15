"""update data analyst profile questions for personalization

Revision ID: 202601090003
Revises: 202601090002
Create Date: 2026-01-09 01:04:52.454824
"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "202601090003"
down_revision = "202601090002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Update data-analyst profile questions Q8-Q10 for personalization."""
    # Update Q8 - Tech/tools preferences
    op.execute(
        "UPDATE question_templates "
        "SET prompt = 'Tools/teknologi apa yang ingin Anda pelajari lebih dalam? "
        "(Sebutkan 2-3, misal: Python, Power BI, SQL)', "
        'metadata = \'{"dimension": "tech-preferences"}\'::json, '
        'expected_values = \'{"accepted_values": ["python", "sql", "tableau", '
        '"power bi", "excel", "r", "pandas", "numpy", "matplotlib", "seaborn", '
        '"looker", "bigquery", "spark"], "allow_custom": true}\'::json '
        "WHERE role_slug = 'data-analyst' AND sequence = 8 AND question_type = 'profile';"
    )

    # Update Q9 - Content duration preference
    op.execute(
        "UPDATE question_templates "
        "SET prompt = 'Preferensi durasi course yang Anda inginkan?', "
        'metadata = \'{"dimension": "content-duration"}\'::json, '
        'expected_values = \'{"accepted_values": ["short", "medium", "long", "any"]}\'::json '
        "WHERE role_slug = 'data-analyst' AND sequence = 9 AND question_type = 'profile';"
    )

    # Update Q10 - Payment preference
    op.execute(
        "UPDATE question_templates "
        "SET prompt = 'Apakah Anda tertarik dengan course berbayar atau gratis?', "
        'metadata = \'{"dimension": "payment-preference"}\'::json, '
        'expected_values = \'{"accepted_values": ["paid", "free", "any"]}\'::json '
        "WHERE role_slug = 'data-analyst' AND sequence = 10 AND question_type = 'profile';"
    )


def downgrade() -> None:
    """Revert to original data-analyst questions."""
    # Revert Q8
    op.execute(
        "UPDATE question_templates "
        "SET prompt = 'Tools apa yang Anda kuasai untuk analisis data? "
        "(contoh: Excel, SQL, Python, Tableau)', "
        'metadata = \'{"dimension": "tools"}\'::json, '
        'expected_values = \'{"accepted_values": ["excel", "sql", "python", '
        '"tableau", "power bi"]}\'::json '
        "WHERE role_slug = 'data-analyst' AND sequence = 8 AND question_type = 'profile';"
    )

    # Revert Q9
    op.execute(
        "UPDATE question_templates "
        "SET prompt = 'Apakah Anda pernah membuat dashboard atau report untuk stakeholders? "
        "Jelaskan singkat.', "
        'metadata = \'{"dimension": "reporting"}\'::json, '
        'expected_values = \'{"accepted_values": ["yes", "no", "dashboard", "report"]}\'::json '
        "WHERE role_slug = 'data-analyst' AND sequence = 9 AND question_type = 'profile';"
    )

    # Revert Q10
    op.execute(
        "UPDATE question_templates "
        "SET prompt = 'Ceritakan project analisis data yang paling berkesan "
        "dan dampaknya bagi bisnis.', "
        'metadata = \'{"dimension": "impact"}\'::json '
        "WHERE role_slug = 'data-analyst' AND sequence = 10 AND question_type = 'profile';"
    )
