"""update data-analyst questions 1-6 with leveled competency set

Revision ID: 202602110003
Revises: 202602110002
Create Date: 2026-02-11 19:45:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "202602110003"
down_revision = "202602110002"
branch_labels = None
depends_on = None


def _to_json(value: object | None) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


def _update_question(
    *,
    sequence: int,
    question_type: str,
    prompt: str,
    difficulty: str,
    metadata: dict[str, object],
    options: list[dict[str, str]] | None = None,
    correct_answer: str | None = None,
    answer_key: str | None = None,
    model_answer: str | None = None,
) -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE question_templates
            SET
                prompt = :prompt,
                difficulty = :difficulty,
                metadata = CAST(:metadata AS json),
                options = CAST(:options AS json),
                correct_answer = :correct_answer,
                answer_key = :answer_key,
                model_answer = :model_answer
            WHERE
                role_slug = 'data-analyst'
                AND sequence = :sequence
                AND question_type = :question_type
                AND is_active = true
            """
        ),
        {
            "sequence": sequence,
            "question_type": question_type,
            "prompt": prompt,
            "difficulty": difficulty,
            "metadata": _to_json(metadata),
            "options": _to_json(options),
            "correct_answer": correct_answer,
            "answer_key": answer_key,
            "model_answer": model_answer,
        },
    )


def upgrade() -> None:
    """Apply leveled Data Analyst competency questions for sequence 1-6."""

    _update_question(
        sequence=1,
        question_type="theoretical",
        prompt="Mean dan median akan berbeda signifikan ketika data memiliki...",
        difficulty="easy",
        metadata={"dimension": "statistics-outlier", "level": 1, "points": 2},
        options=[
            {"id": "A", "text": "Data yang simetris"},
            {"id": "B", "text": "Distribusi normal"},
            {"id": "C", "text": "Outlier ekstrem"},
            {"id": "D", "text": "Jumlah data genap"},
        ],
        correct_answer="C",
        answer_key=(
            "Outlier ekstrem menarik nilai mean lebih kuat daripada median, sehingga "
            "keduanya bisa berbeda signifikan."
        ),
        model_answer=("Outlier ekstrem memengaruhi mean lebih besar dibanding median."),
    )

    _update_question(
        sequence=2,
        question_type="theoretical",
        prompt=(
            "Query berikut akan menghasilkan apa?\n"
            "SELECT COUNT(DISTINCT user_id)\n"
            "FROM transactions\n"
            "WHERE transaction_date >= '2025-01-01'\n"
            "AND transaction_date < '2025-02-01';"
        ),
        difficulty="medium",
        metadata={"dimension": "sql-distinct", "level": 2, "points": 4},
        options=[
            {
                "id": "A",
                "text": "Jumlah seluruh transaksi yang terjadi pada Januari 2025",
            },
            {
                "id": "B",
                "text": "Jumlah user unik yang bertransaksi pada Januari 2025",
            },
            {
                "id": "C",
                "text": "Jumlah user baru yang mendaftar pada Januari 2025",
            },
            {
                "id": "D",
                "text": "Jumlah user unik yang bertransaksi sepanjang tahun 2025",
            },
        ],
        correct_answer="B",
        answer_key=(
            "COUNT(DISTINCT user_id) menghitung user unik dalam window tanggal yang difilter."
        ),
        model_answer="Jumlah user unik yang melakukan transaksi pada Januari 2025.",
    )

    _update_question(
        sequence=3,
        question_type="theoretical",
        prompt=(
            "Dalam dashboard funnel, conversion rate per channel naik tetapi conversion rate "
            "total turun. Penyebab paling mungkin adalah..."
        ),
        difficulty="hard",
        metadata={"dimension": "simpson-paradox", "level": 3, "points": 6},
        options=[
            {
                "id": "A",
                "text": "Data pasti salah karena metrik channel dan total harus selalu searah",
            },
            {
                "id": "B",
                "text": (
                    "Terjadi Simpson's paradox akibat perubahan proporsi trafik antar channel"
                ),
            },
            {"id": "C", "text": "COUNT(DISTINCT) otomatis memperbaiki bias komposisi"},
            {"id": "D", "text": "Median conversion tidak bisa dipakai untuk data funnel"},
        ],
        correct_answer="B",
        answer_key=(
            "Setiap segmen bisa membaik, namun agregat turun karena komposisi volume berubah."
        ),
        model_answer=(
            "Kemungkinan Simpson's paradox karena pergeseran proporsi trafik antar channel."
        ),
    )

    _update_question(
        sequence=4,
        question_type="essay",
        prompt=(
            "Diberikan tabel transaksi dengan kolom user_id, amount, transaction_date, "
            "email, dan city. Jelaskan langkah data cleaning dan validasi sebelum analisis."
        ),
        difficulty="easy",
        metadata={"dimension": "data-cleaning-validation", "level": 4, "points": 8},
        answer_key=(
            "Cek null, duplikasi, tipe data tanggal/angka, format email, nilai amount negatif, "
            "outlier, dan dokumentasikan rule cleaning."
        ),
        model_answer=(
            "Profiling data, missing value handling, dedup, standardisasi city, validasi email, "
            "normalisasi tanggal, dan quality report sebelum analisis."
        ),
    )

    _update_question(
        sequence=5,
        question_type="essay",
        prompt=(
            "Tulis SQL untuk menghitung Monthly Active Users (MAU) dan persentase repeat user "
            "per bulan dari tabel transactions(user_id, transaction_date)."
        ),
        difficulty="medium",
        metadata={"dimension": "sql-mau-repeat", "level": 5, "points": 12},
        answer_key=(
            "Gunakan DATE_TRUNC per bulan, COUNT(DISTINCT user_id) untuk MAU, dan repeat user "
            "dengan agregasi transaksi user per bulan (>1)."
        ),
        model_answer=(
            "CTE monthly_user_txn -> month,user_id,txn_count; agregasi MAU, repeat_users, "
            "repeat_rate = repeat_users::float/MAU."
        ),
    )

    _update_question(
        sequence=6,
        question_type="essay",
        prompt=(
            "Case: Revenue naik 12% MoM, tetapi jumlah pelanggan aktif turun 8% dan return "
            "rate naik 15%. Buat analytical memo yang menjelaskan hipotesis akar masalah, "
            "analisis lanjutan yang perlu dijalankan, dan rekomendasi aksi prioritas."
        ),
        difficulty="hard",
        metadata={"dimension": "business-reasoning", "level": 6, "points": 18},
        answer_key=(
            "Perlu reasoning bisnis + metrik: breakdown cohort/produk/channel, cek kontribusi "
            "pricing vs volume, sumber return, dan eksperimen prioritas terukur."
        ),
        model_answer=(
            "Revenue bisa naik karena AOV, tapi retensi turun. Lanjutkan analisis cohort, "
            "segmentasi penyebab return, lalu susun action plan dengan owner, timeline, KPI."
        ),
    )


def downgrade() -> None:
    """No automatic downgrade for content migration."""
    pass
