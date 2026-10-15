"""update existing profile questions Q8-Q10 in database

Revision ID: 202601090001
Revises: 202601082201
Create Date: 2026-01-09 00:01:00

Updates existing profile questions in question_templates table:
- Q8 (Seq 8): Technology preferences with allow_custom
- Q9 (Seq 9): Content duration preference
- Q10 (Seq 10): Payment preference
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "202601090001"
down_revision = "202602090001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Update profile questions Q8-Q10 for personalization."""
    # Update Q8 - Technology preferences
    op.execute("""
        UPDATE question_templates
        SET
            prompt = 'Teknologi/tools apa yang ingin Anda pelajari lebih dalam? '
                     '(Sebutkan 2-3, misal: Docker, AWS, GraphQL)',
            metadata = '{"dimension": "tech-preferences"}'::json,
            expected_values = ('{"accepted_values": ["docker", "kubernetes", "aws", ' ||
                '"gcp", "azure", "graphql", "redis", "kafka", "microservices", ' ||
                '"ci/cd", "terraform", "mongodb", "postgresql", "elasticsearch"], ' ||
                '"allow_custom": true}')::json
        WHERE role_slug = 'backend-engineer'
        AND sequence = 8
        AND question_type = 'profile';
    """)

    # Update Q9 - Content duration preference
    op.execute("""
        UPDATE question_templates
        SET
            prompt = 'Preferensi durasi course yang Anda inginkan?',
            metadata = '{"dimension": "content-duration"}'::json,
            expected_values = '{"accepted_values": ["short", "medium", "long", "any"]}'::json
        WHERE role_slug = 'backend-engineer'
        AND sequence = 9
        AND question_type = 'profile';
    """)

    # Update Q10 - Payment preference
    op.execute("""
        UPDATE question_templates
        SET
            prompt = 'Apakah Anda tertarik dengan course berbayar atau gratis?',
            metadata = '{"dimension": "payment-preference"}'::json,
            expected_values = '{"accepted_values": ["paid", "free", "any"]}'::json
        WHERE role_slug = 'backend-engineer'
        AND sequence = 10
        AND question_type = 'profile';
    """)


def downgrade() -> None:
    """Revert profile questions to original form."""
    # Revert Q8
    op.execute("""
        UPDATE question_templates
        SET
            prompt = 'Framework dan bahasa pemrograman apa yang paling sering Anda gunakan?',
            metadata = '{"dimension": "tech-stack"}'::json,
            expected_values = ('{"accepted_values": ["node", "python", ' ||
                '"go", "java", "ruby"]}')::json
        WHERE role_slug = 'backend-engineer'
        AND sequence = 8
        AND question_type = 'profile';
    """)

    # Revert Q9
    op.execute("""
        UPDATE question_templates
        SET
            prompt = 'Apakah Anda pernah deploy aplikasi ke production? '
                     || 'Jelaskan platform yang digunakan.',
            metadata = '{"dimension": "deployment"}'::json,
            expected_values = ('{"accepted_values": ["aws", "gcp", "azure", ' ||
                '"render", "docker"]}')::jsonb
        WHERE role_slug = 'backend-engineer'
        AND sequence = 9
        AND question_type = 'profile';
    """)

    # Revert Q10
    op.execute("""
        UPDATE question_templates
        SET
            prompt = 'Ceritakan tantangan teknis terbesar yang pernah Anda hadapi '
                     || 'dan bagaimana solusinya.',
            metadata = '{"dimension": "problem-solving"}'::json,
            expected_values = ('{\"accepted_values\": [\"outage\", \"scaling\", ' ||
                '\"migration\", \"refactor\"]}')::json
        WHERE role_slug = 'backend-engineer'
        AND sequence = 10
        AND question_type = 'profile';
    """)
