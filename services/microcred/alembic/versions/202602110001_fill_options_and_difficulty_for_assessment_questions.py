"""fill options, correct answers, and difficulty for core assessment questions

Revision ID: 202602110001
Revises: fe375ee7f2f9
Create Date: 2026-02-11 19:00:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "202602110001"
down_revision = "fe375ee7f2f9"
branch_labels = None
depends_on = None


def _to_json(value: object | None) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


def _update_template(
    *,
    role_slug: str,
    sequence: int,
    question_type: str,
    difficulty: str | None = None,
    options: list[dict[str, str]] | None = None,
    correct_answer: str | None = None,
    expected_values: dict | None = None,
) -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE question_templates
            SET
                difficulty = COALESCE(:difficulty, difficulty),
                options = COALESCE(CAST(:options AS json), options),
                correct_answer = COALESCE(:correct_answer, correct_answer),
                expected_values = CAST(:expected_values AS json)
            WHERE
                role_slug = :role_slug
                AND sequence = :sequence
                AND question_type = :question_type
                AND is_active = true
            """
        ),
        {
            "role_slug": role_slug,
            "sequence": sequence,
            "question_type": question_type,
            "difficulty": difficulty,
            "options": _to_json(options),
            "correct_answer": correct_answer,
            "expected_values": _to_json(expected_values),
        },
    )


def upgrade() -> None:
    """Apply question data fix for options and difficulty."""

    be_q1_options = [
        {
            "id": "A",
            "text": (
                "FastAPI async unggul untuk I/O-bound high concurrency karena "
                "non-blocking; framework synchronous lebih mudah untuk flow sederhana."
            ),
        },
        {
            "id": "B",
            "text": (
                "Framework synchronous selalu lebih cepat di beban tinggi karena "
                "tiap request diproses paralel otomatis."
            ),
        },
        {
            "id": "C",
            "text": "FastAPI async hanya cocok untuk aplikasi kecil dengan traffic rendah.",
        },
        {
            "id": "D",
            "text": "Tidak ada perbedaan signifikan karena model eksekusi keduanya identik.",
        },
    ]
    be_q2_options = [
        {
            "id": "A",
            "text": (
                "Idempotensi memastikan request berulang memberi efek akhir yang sama; "
                "gunakan idempotency key unik dan simpan hasil submit pertama."
            ),
        },
        {
            "id": "B",
            "text": (
                "Idempotensi berarti request kedua harus selalu ditolak 500 agar "
                "tidak terjadi duplikasi."
            ),
        },
        {
            "id": "C",
            "text": "Idempotensi hanya berlaku di GET, bukan endpoint submit berbasis POST.",
        },
        {
            "id": "D",
            "text": "Idempotensi cukup mengandalkan cache browser tanpa backend state.",
        },
    ]
    be_q3_options = [
        {
            "id": "A",
            "text": (
                "Untuk MVP 4 minggu, modular monolith biasanya lebih cepat dikirim; "
                "microservice dipilih jika domain dan ownership tim sudah matang."
            ),
        },
        {
            "id": "B",
            "text": "Microservice selalu lebih cepat dibuat untuk MVP karena stack bebas.",
        },
        {
            "id": "C",
            "text": "Modular monolith tidak bisa menjalankan worker RAG/GPT async.",
        },
        {
            "id": "D",
            "text": "Keduanya tidak cocok untuk integrasi AI tanpa event sourcing penuh.",
        },
    ]

    da_q1_options = [
        {
            "id": "A",
            "text": (
                "Explainability adalah kemampuan menjelaskan alasan rekomendasi; "
                "ukur dengan reason code, trace fitur, dan pemahaman user/advisor."
            ),
        },
        {"id": "B", "text": "Explainability sama dengan akurasi model."},
        {"id": "C", "text": "Explainability hanya dibutuhkan untuk model linear."},
        {
            "id": "D",
            "text": "Explainability cukup dinilai dari jumlah item rekomendasi.",
        },
    ]
    da_q2_options = [
        {
            "id": "A",
            "text": (
                "Latency memengaruhi trust; visualisasikan p50/p95/p99, SLA target, "
                "dan alert breach di dashboard."
            ),
        },
        {"id": "B", "text": "Latency tidak memengaruhi trust advisor."},
        {"id": "C", "text": "Cukup tampilkan rata-rata latency bulanan tanpa percentile."},
        {"id": "D", "text": "Dashboard SLA tidak diperlukan jika ada cache."},
    ]
    da_q3_options = [
        {
            "id": "A",
            "text": (
                "RAG zero-shot cepat diadopsi, taxonomy-based RAG lebih konsisten "
                "untuk mapping skill-course namun butuh kurasi."
            ),
        },
        {"id": "B", "text": "Taxonomy-based RAG tidak bisa dipakai untuk micro-credential."},
        {"id": "C", "text": "Zero-shot RAG selalu lebih akurat dari taxonomy."},
        {"id": "D", "text": "Keduanya identik karena sama-sama pakai vector DB."},
    ]

    profile_experience_options = [
        {"id": "A", "text": "<1 tahun"},
        {"id": "B", "text": "1-3 tahun"},
        {"id": "C", "text": "3-5 tahun"},
        {"id": "D", "text": ">5 tahun"},
    ]
    profile_experience_values = {
        "accepted_values": ["A", "B", "C", "D"],
        "allow_custom": False,
    }

    profile_duration_options = [
        {"id": "A", "text": "Short (<2 jam)"},
        {"id": "B", "text": "Medium (2-6 jam)"},
        {"id": "C", "text": "Long (>6 jam)"},
        {"id": "D", "text": "Any duration"},
    ]
    profile_duration_values = {
        "accepted_values": ["A", "B", "C", "D"],
        "allow_custom": False,
    }

    profile_payment_options = [
        {"id": "A", "text": "Paid"},
        {"id": "B", "text": "Free"},
        {"id": "C", "text": "Keduanya (Paid & Free)"},
    ]
    profile_payment_values = {
        "accepted_values": ["A", "B", "C"],
        "allow_custom": False,
    }

    _update_template(
        role_slug="backend-engineer",
        sequence=1,
        question_type="theoretical",
        difficulty="easy",
        options=be_q1_options,
        correct_answer="A",
        expected_values=None,
    )
    _update_template(
        role_slug="backend-engineer",
        sequence=2,
        question_type="theoretical",
        difficulty="medium",
        options=be_q2_options,
        correct_answer="A",
        expected_values=None,
    )
    _update_template(
        role_slug="backend-engineer",
        sequence=3,
        question_type="theoretical",
        difficulty="hard",
        options=be_q3_options,
        correct_answer="A",
        expected_values=None,
    )

    _update_template(
        role_slug="data-analyst",
        sequence=1,
        question_type="theoretical",
        difficulty="easy",
        options=da_q1_options,
        correct_answer="A",
        expected_values=None,
    )
    _update_template(
        role_slug="data-analyst",
        sequence=2,
        question_type="theoretical",
        difficulty="medium",
        options=da_q2_options,
        correct_answer="A",
        expected_values=None,
    )
    _update_template(
        role_slug="data-analyst",
        sequence=3,
        question_type="theoretical",
        difficulty="hard",
        options=da_q3_options,
        correct_answer="A",
        expected_values=None,
    )

    for role in ("backend-engineer", "data-analyst"):
        _update_template(
            role_slug=role,
            sequence=4,
            question_type="essay",
            difficulty="easy",
            expected_values=None,
        )
        _update_template(
            role_slug=role,
            sequence=5,
            question_type="essay",
            difficulty="medium",
            expected_values=None,
        )
        _update_template(
            role_slug=role,
            sequence=6,
            question_type="essay",
            difficulty="hard",
            expected_values=None,
        )

    for role in ("backend-engineer", "data-analyst"):
        _update_template(
            role_slug=role,
            sequence=7,
            question_type="profile",
            options=profile_experience_options,
            expected_values=profile_experience_values,
        )
        _update_template(
            role_slug=role,
            sequence=9,
            question_type="profile",
            options=profile_duration_options,
            expected_values=profile_duration_values,
        )
        _update_template(
            role_slug=role,
            sequence=10,
            question_type="profile",
            options=profile_payment_options,
            expected_values=profile_payment_values,
        )


def downgrade() -> None:
    """Revert question data to previous defaults."""
    bind = op.get_bind()

    bind.execute(
        sa.text(
            """
            UPDATE question_templates
            SET options = NULL, correct_answer = NULL, expected_values = NULL,
                difficulty = 'medium'
            WHERE role_slug IN ('backend-engineer', 'data-analyst')
              AND sequence IN (1, 2, 3, 7)
              AND question_type IN ('theoretical', 'profile')
              AND is_active = true
            """
        )
    )

    bind.execute(
        sa.text(
            """
            UPDATE question_templates
            SET difficulty = 'medium'
            WHERE role_slug IN ('backend-engineer', 'data-analyst')
              AND sequence IN (4, 5, 6)
              AND question_type = 'essay'
              AND is_active = true
            """
        )
    )

    bind.execute(
        sa.text(
            """
            UPDATE question_templates
            SET
                options = NULL,
                expected_values = '{"accepted_values": ["short", "medium", "long", "any"]}'::json
            WHERE role_slug IN ('backend-engineer', 'data-analyst')
              AND sequence = 9
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
                options = NULL,
                expected_values = '{"accepted_values": ["paid", "free", "any"]}'::json
            WHERE role_slug IN ('backend-engineer', 'data-analyst')
              AND sequence = 10
              AND question_type = 'profile'
              AND is_active = true
            """
        )
    )
