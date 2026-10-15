"""update backend questions 1-6 with leveled competency set

Revision ID: 202602110002
Revises: 202602110001
Create Date: 2026-02-11 19:20:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "202602110002"
down_revision = "202602110001"
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
                role_slug = 'backend-engineer'
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
    """Apply new leveled backend competency questions for sequence 1-6."""

    _update_question(
        sequence=1,
        question_type="theoretical",
        prompt=(
            "HTTP status code yang paling tepat untuk request valid tapi tidak memiliki "
            "akses ke resource adalah..."
        ),
        difficulty="easy",
        metadata={"dimension": "http-authz", "level": 1, "points": 2},
        options=[
            {"id": "A", "text": "400 Bad Request"},
            {"id": "B", "text": "401 Unauthorized"},
            {"id": "C", "text": "403 Forbidden"},
            {"id": "D", "text": "404 Not Found"},
        ],
        correct_answer="C",
        answer_key=(
            "403 Forbidden dipakai saat user sudah terautentikasi tetapi tidak berhak "
            "mengakses resource. 401 untuk auth yang tidak valid atau belum ada."
        ),
        model_answer=(
            "403 Forbidden dipakai saat user sudah terautentikasi tetapi tidak berhak "
            "mengakses resource. 401 untuk auth yang tidak valid atau belum ada."
        ),
    )

    _update_question(
        sequence=2,
        question_type="theoretical",
        prompt=(
            "Query: SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC LIMIT 20; "
            "Index yang paling efektif adalah..."
        ),
        difficulty="medium",
        metadata={"dimension": "database-indexing", "level": 2, "points": 4},
        options=[
            {"id": "A", "text": "index (created_at)"},
            {"id": "B", "text": "index (user_id)"},
            {"id": "C", "text": "composite index (user_id, created_at)"},
            {"id": "D", "text": "fulltext index pada orders"},
        ],
        correct_answer="C",
        answer_key=(
            "Karena query memfilter user_id dan mengurutkan created_at, composite index "
            "(user_id, created_at) paling optimal untuk akses data ini."
        ),
        model_answer=(
            "Karena query memfilter user_id dan mengurutkan created_at, composite index "
            "(user_id, created_at) paling optimal untuk akses data ini."
        ),
    )

    _update_question(
        sequence=3,
        question_type="theoretical",
        prompt=(
            "Pada arsitektur microservices, untuk memastikan operasi create payment tidak "
            "dobel saat client retry (timeout), pendekatan paling tepat adalah..."
        ),
        difficulty="hard",
        metadata={"dimension": "idempotency", "level": 3, "points": 6},
        options=[
            {"id": "A", "text": "Client dilarang retry"},
            {"id": "B", "text": "Tambahkan delay di client sebelum retry"},
            {
                "id": "C",
                "text": "Gunakan Idempotency-Key dan simpan hasil berdasarkan key",
            },
            {"id": "D", "text": "Gunakan GET instead of POST"},
        ],
        correct_answer="C",
        answer_key=(
            "Retry request adalah normal pada jaringan tidak stabil. Idempotency key dan "
            "penyimpanan hasil by key mencegah operasi create terproses ganda."
        ),
        model_answer=(
            "Retry request adalah normal pada jaringan tidak stabil. Idempotency key dan "
            "penyimpanan hasil by key mencegah operasi create terproses ganda."
        ),
    )

    _update_question(
        sequence=4,
        question_type="essay",
        prompt=(
            "Jelaskan perbedaan PUT vs PATCH, lalu beri contoh request payload untuk "
            "update user."
        ),
        difficulty="easy",
        metadata={"dimension": "http-methods", "level": 4, "points": 8},
        answer_key=(
            "PUT = full replacement resource (idempotent), PATCH = partial update. "
            "Sertakan contoh payload PUT dan PATCH, serta implikasi field yang tidak dikirim."
        ),
        model_answer=(
            "PUT mengganti seluruh representasi user, PATCH hanya field tertentu. Contoh: "
            "PUT /users/10 kirim name+email+field penting lain, PATCH /users/10 bisa "
            '{"email": "baru@x.com"}. Jelaskan idempotency dan field missing.'
        ),
    )

    _update_question(
        sequence=5,
        question_type="essay",
        prompt=(
            "Buat pseudo-code atau kode untuk endpoint POST /login yang memvalidasi input, "
            "verifikasi password hash, mengembalikan JWT ber-exp, dan mapping error "
            "400/401/500 secara tepat."
        ),
        difficulty="medium",
        metadata={"dimension": "auth-implementation", "level": 5, "points": 12},
        answer_key=(
            "Harus ada: validasi input, lookup user by email, verify hash bcrypt/argon2, "
            "JWT dengan claim sub dan exp, serta status code 400/401/500 sesuai kasus."
        ),
        model_answer=(
            "if !email||!password -> 400; user=findByEmail; if !user -> 401; "
            "if !verify(password, hash) -> 401; token=jwt.sign({sub,exp}); return 200; "
            "unexpected -> 500 tanpa bocor info sensitif."
        ),
    )

    _update_question(
        sequence=6,
        question_type="essay",
        prompt=(
            "Desain mekanisme rate limiting untuk public API multi-instance yang bisa "
            "handle burst, aman, efisien, dan mengembalikan response informatif saat "
            "limit tercapai."
        ),
        difficulty="hard",
        metadata={"dimension": "rate-limiting", "level": 6, "points": 18},
        answer_key=(
            "Pilih algoritma Token Bucket/Sliding Window, gunakan Redis shared store, "
            "atomicity via Lua/atomic ops, key strategy per user/apiKey/IP, dan response "
            "429 + Retry-After + rate-limit headers."
        ),
        model_answer=(
            "Gunakan token bucket di Redis untuk multi-instance, key rate:{apiKey}:{route}, "
            "consume token atomik via Lua script, support burst dan fairness. Saat limit habis "
            "kirim 429 dengan Retry-After, X-RateLimit-Limit, Remaining, dan Reset."
        ),
    )


def downgrade() -> None:
    """No automatic downgrade for content migration."""
    pass
