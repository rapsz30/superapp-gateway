"""update profile question 7 to use project count + checklist scoring

Revision ID: 202602140001
Revises: 202602110004
Create Date: 2026-02-14 18:30:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "202602140001"
down_revision = "202602110004"
branch_labels = None
depends_on = None


def _to_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def _set_q7(
    *,
    role_slug: str,
    prompt: str,
    options: list[dict[str, str]],
    expected_values: dict[str, object],
    captures: list[str],
) -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE question_templates
            SET
                prompt = :prompt,
                options = CAST(:options AS json),
                expected_values = CAST(:expected_values AS json),
                metadata = CAST(
                    jsonb_set(
                        COALESCE(CAST(metadata AS jsonb), '{}'::jsonb),
                        '{captures}',
                        CAST(:captures AS jsonb),
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
            "expected_values": _to_json(expected_values),
            "captures": _to_json(captures),
        },
    )


def upgrade() -> None:
    """Set Q7 to project-count input plus checklist scoring."""
    project_checklist_expected_values = {
        "type": "project_checklist",
        "project_count": {
            "ranges": [
                {"min": 0, "max": 1, "score": 10},
                {"min": 2, "max": 4, "score": 25},
                {"min": 5, "max": 8, "score": 40},
                {"min": 9, "max": 999, "score": 60},
            ]
        },
        "checklist_scoring": {
            "personal": 5,
            "kampus": 10,
            "production": 15,
            "lintas-domain": 10,
        },
        "max_raw_score": 100,
        "accepted_values": ["personal", "kampus", "production", "lintas-domain"],
        "legacy_option_mapping": {
            "A": {"project_count": 1, "selected_options": ["personal"]},
            "B": {"project_count": 3, "selected_options": ["personal", "kampus"]},
            "C": {
                "project_count": 6,
                "selected_options": ["personal", "kampus", "production"],
            },
            "D": {
                "project_count": 9,
                "selected_options": ["personal", "kampus", "production", "lintas-domain"],
            },
        },
        "allow_custom": False,
    }

    _set_q7(
        role_slug="backend-engineer",
        prompt=(
            "Masukkan total project backend yang pernah Anda kerjakan, lalu pilih semua "
            "konteks project yang pernah Anda tangani (checklist)."
        ),
        options=[
            {"id": "personal", "text": "Project personal"},
            {"id": "kampus", "text": "Project kampus/bootcamp"},
            {"id": "production", "text": "Project production (real user)"},
            {"id": "lintas-domain", "text": "Project lintas domain/industri"},
        ],
        expected_values=project_checklist_expected_values,
        captures=["project_count", "project_contexts"],
    )

    _set_q7(
        role_slug="data-analyst",
        prompt=(
            "Masukkan total project analitik yang pernah Anda kerjakan, lalu pilih "
            "semua konteks project yang pernah Anda tangani (checklist)."
        ),
        options=[
            {"id": "personal", "text": "Project personal"},
            {"id": "kampus", "text": "Project kampus/bootcamp"},
            {"id": "production", "text": "Project production (real stakeholder)"},
            {"id": "lintas-domain", "text": "Project lintas domain/industri"},
        ],
        expected_values=project_checklist_expected_values,
        captures=["project_count", "project_contexts"],
    )


def downgrade() -> None:
    """Restore Q7 options that combine years and project counts."""
    legacy_expected_values = {
        "accepted_values": ["A", "B", "C", "D"],
        "allow_custom": False,
    }

    _set_q7(
        role_slug="backend-engineer",
        prompt=(
            "Profil pengalaman Anda paling sesuai yang mana terkait lama programming dan "
            "jumlah project backend yang pernah dikerjakan?"
        ),
        options=[
            {"id": "A", "text": "<1 tahun programming, 0-1 project backend"},
            {"id": "B", "text": "1-2 tahun programming, 2-4 project backend (personal/kampus)"},
            {
                "id": "C",
                "text": "2-4 tahun programming, 5-8 project backend (termasuk production)",
            },
            {
                "id": "D",
                "text": ">4 tahun programming, >8 project backend lintas domain/production",
            },
        ],
        expected_values=legacy_expected_values,
        captures=["programming_years", "project_count"],
    )

    _set_q7(
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
        expected_values=legacy_expected_values,
        captures=["programming_years", "project_count"],
    )
