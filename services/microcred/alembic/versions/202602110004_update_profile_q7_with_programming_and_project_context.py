"""update profile question 7 to include programming years and project experience

Revision ID: 202602110004
Revises: 202602110003
Create Date: 2026-02-11 20:00:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "202602110004"
down_revision = "202602110003"
branch_labels = None
depends_on = None


def _to_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def _update_q7(
    *,
    role_slug: str,
    prompt: str,
    options: list[dict[str, str]],
) -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE question_templates
            SET
                prompt = :prompt,
                options = CAST(:options AS json),
                expected_values = (
                    '{"accepted_values": ["A", "B", "C", "D"], "allow_custom": false}'::json
                ),
                metadata = CAST(
                    jsonb_set(
                        COALESCE(CAST(metadata AS jsonb), '{}'::jsonb),
                        '{captures}',
                        '["programming_years","project_count"]'::jsonb,
                        true
                    ) AS json
                )
            WHERE
                role_slug = :role_slug
                AND sequence = 7
                AND question_type = 'profile'
                AND is_active = true
            """
        ),
        {
            "role_slug": role_slug,
            "prompt": prompt,
            "options": _to_json(options),
        },
    )


def upgrade() -> None:
    """Apply profile question context update for backend and data analyst tracks."""

    _update_q7(
        role_slug="backend-engineer",
        prompt=(
            "Profil pengalaman Anda paling sesuai yang mana terkait lama programming dan "
            "jumlah project backend yang pernah dikerjakan?"
        ),
        options=[
            {"id": "A", "text": "<1 tahun programming, 0-1 project backend"},
            {
                "id": "B",
                "text": "1-2 tahun programming, 2-4 project backend (personal/kampus)",
            },
            {
                "id": "C",
                "text": "2-4 tahun programming, 5-8 project backend (termasuk production)",
            },
            {
                "id": "D",
                "text": ">4 tahun programming, >8 project backend lintas domain/production",
            },
        ],
    )

    _update_q7(
        role_slug="data-analyst",
        prompt=(
            "Profil pengalaman Anda paling sesuai yang mana terkait lama programming/analisis "
            "data dan jumlah project analitik yang pernah dikerjakan?"
        ),
        options=[
            {"id": "A", "text": "<1 tahun, 0-1 project analitik"},
            {"id": "B", "text": "1-2 tahun, 2-4 project SQL/dashboard"},
            {"id": "C", "text": "2-4 tahun, 5-8 project analitik end-to-end"},
            {
                "id": "D",
                "text": ">4 tahun, >8 project analitik dengan stakeholder production",
            },
        ],
    )


def downgrade() -> None:
    """Revert prompt/options to simple year-based options."""
    bind = op.get_bind()

    bind.execute(
        sa.text(
            """
            UPDATE question_templates
            SET
                prompt = 'Berapa tahun pengalaman Anda sebagai Backend Engineer?',
                options = '[
                  {"id":"A","text":"<1 tahun"},
                  {"id":"B","text":"1-3 tahun"},
                  {"id":"C","text":"3-5 tahun"},
                  {"id":"D","text":">5 tahun"}
                ]'::json,
                expected_values = (
                    '{"accepted_values": ["A", "B", "C", "D"], "allow_custom": false}'::json
                ),
                metadata = CAST(CAST(metadata AS jsonb) - 'captures' AS json)
            WHERE role_slug = 'backend-engineer'
              AND sequence = 7
              AND question_type = 'profile'
              AND is_active = true
            """
        )
    )

    bind.execute(
        sa.text(
            """
            UPDATE question_templates
            SET
                prompt = 'Berapa tahun pengalaman Anda sebagai Data Analyst?',
                options = '[
                  {"id":"A","text":"<1 tahun"},
                  {"id":"B","text":"1-3 tahun"},
                  {"id":"C","text":"3-5 tahun"},
                  {"id":"D","text":">5 tahun"}
                ]'::json,
                expected_values = (
                    '{"accepted_values": ["A", "B", "C", "D"], "allow_custom": false}'::json
                ),
                metadata = CAST(CAST(metadata AS jsonb) - 'captures' AS json)
            WHERE role_slug = 'data-analyst'
              AND sequence = 7
              AND question_type = 'profile'
              AND is_active = true
            """
        )
    )
