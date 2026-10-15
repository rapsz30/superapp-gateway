"""Initial schema for roles, questions, and assessments

Revision ID: 202412250001
Revises:
Create Date: 2024-12-25 00:01:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "202412250001"
down_revision = None
branch_labels = None
depends_on = None

question_type_enum = sa.Enum(
    "theoretical",
    "essay",
    "profile",
    name="question_type",
)
assessment_status_enum = sa.Enum(
    "draft",
    "in_progress",
    "completed",
    name="assessment_status",
)


def upgrade() -> None:
    op.create_table(
        "role_catalog",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=64), nullable=False, unique=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
    )

    op.create_table(
        "question_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "role_slug",
            sa.String(length=64),
            sa.ForeignKey("role_catalog.slug", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("question_type", question_type_enum, nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
    )

    op.create_table(
        "assessments",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("owner_id", sa.String(length=64), nullable=False, index=True),
        sa.Column(
            "role_slug",
            sa.String(length=64),
            sa.ForeignKey("role_catalog.slug", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("status", assessment_status_enum, nullable=False, index=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "assessment_question_snapshots",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "assessment_id",
            sa.String(length=36),
            sa.ForeignKey("assessments.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "question_template_id",
            sa.Integer(),
            sa.ForeignKey("question_templates.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("question_type", question_type_enum, nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
    )

    op.create_table(
        "assessment_responses",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "assessment_id",
            sa.String(length=36),
            sa.ForeignKey("assessments.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "question_snapshot_id",
            sa.String(length=36),
            sa.ForeignKey("assessment_question_snapshots.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("response_data", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    roles = [
        {
            "slug": "backend-engineer",
            "name": "Backend Engineer",
            "description": (
                "Async-first service work: queue orchestration, " "scoring, and recommendations."
            ),
        },
        {
            "slug": "data-analyst",
            "name": "Data Analyst",
            "description": (
                "Analytics and transparency focus: RAG insights, "
                "observability, and storytelling."
            ),
        },
    ]
    op.bulk_insert(
        sa.table(
            "role_catalog",
            sa.column("slug", sa.String()),
            sa.column("name", sa.String()),
            sa.column("description", sa.Text()),
        ),
        roles,
    )

    def question_row(
        role_slug: str,
        sequence: int,
        qtype: str,
        prompt: str,
        metadata: dict[str, str],
    ) -> dict:
        return {
            "role_slug": role_slug,
            "sequence": sequence,
            "question_type": qtype,
            "prompt": prompt,
            "metadata": metadata,
        }

    backend_questions = [
        question_row(
            "backend-engineer",
            1,
            "theoretical",
            (
                "Jelaskan perbedaan utama antara FastAPI async dengan "
                "framework synchronous untuk API backend berbeban tinggi."
            ),
            {"dimension": "architecture"},
        ),
        question_row(
            "backend-engineer",
            2,
            "theoretical",
            (
                "Apa arti idempotensi pada endpoint submit assessment dan "
                "bagaimana cara menjaganya ketika job async digunakan?"
            ),
            {"dimension": "reliability"},
        ),
        question_row(
            "backend-engineer",
            3,
            "theoretical",
            (
                "Bandingkan modular monolith vs microservice untuk MVP "
                "empat minggu yang mengandalkan RAG dan GPT workers."
            ),
            {"dimension": "tradeoff"},
        ),
        question_row(
            "backend-engineer",
            4,
            "essay",
            (
                "Rancang alur scoring hybrid (rule + GPT) agar SLA <10 "
                "detik tercapai. Jelaskan komponen utama dan komunikasi "
                "antar komponen."
            ),
            {"dimension": "system-design"},
        ),
        question_row(
            "backend-engineer",
            5,
            "essay",
            (
                "Platform memiliki requirement audit trail. Jelaskan "
                "pendekatan logging dan storage yang memastikan jejak "
                "rekomendasi bisa dilacak."
            ),
            {"dimension": "observability"},
        ),
        question_row(
            "backend-engineer",
            6,
            "essay",
            (
                "Bagaimana strategi fallback ketika GPT atau vector store "
                "gagal namun hasil rekomendasi harus tetap diberikan?"
            ),
            {"dimension": "resilience"},
        ),
        question_row(
            "backend-engineer",
            7,
            "profile",
            "Berapa pengalaman Anda bekerja dengan Redis atau message queue sejenis?",
            {"dimension": "experience"},
        ),
        question_row(
            "backend-engineer",
            8,
            "profile",
            (
                "Tumpukan teknologi apa yang paling familiar untuk "
                "menjalankan FastAPI di produksi?"
            ),
            {"dimension": "stack"},
        ),
        question_row(
            "backend-engineer",
            9,
            "profile",
            "Apa prioritas utama Anda: throughput, cost, atau transparansi?",
            {"dimension": "priority"},
        ),
        question_row(
            "backend-engineer",
            10,
            "profile",
            ("Sebutkan satu tantangan terbesar saat mengoperasikan " "layanan async sebelumnya."),
            {"dimension": "pain-point"},
        ),
    ]

    analyst_questions = [
        question_row(
            "data-analyst",
            1,
            "theoretical",
            (
                "Apa arti explainability dalam konteks rekomendasi "
                "micro-credential dan bagaimana cara mengukurnya?"
            ),
            {"dimension": "explainability"},
        ),
        question_row(
            "data-analyst",
            2,
            "theoretical",
            (
                "Mengapa latency penting untuk trust advisor dan bagaimana "
                "cara memvisualisasikan SLA di dashboard?"
            ),
            {"dimension": "observability"},
        ),
        question_row(
            "data-analyst",
            3,
            "theoretical",
            (
                "Bandingkan teknik RAG zero-shot vs RAG berbasis taxonomy "
                "untuk katalog micro-credential."
            ),
            {"dimension": "rag"},
        ),
        question_row(
            "data-analyst",
            4,
            "essay",
            (
                "Deskripsikan dataset minimal yang dibutuhkan untuk "
                "memvalidasi skor rekomendasi serta bagaimana Anda menilai "
                "kualitasnya."
            ),
            {"dimension": "dataset"},
        ),
        question_row(
            "data-analyst",
            5,
            "essay",
            (
                "Bagaimana memetakan feedback advisor/students menjadi "
                "sinyal yang siap dipakai tuning model rekomendasi?"
            ),
            {"dimension": "feedback"},
        ),
        question_row(
            "data-analyst",
            6,
            "essay",
            (
                "Tulis contoh ringkasan naratif hasil assessment yang "
                "transparan dan mudah dipahami bagi mahasiswa."
            ),
            {"dimension": "storytelling"},
        ),
        question_row(
            "data-analyst",
            7,
            "profile",
            "Apa pengalaman Anda dengan BI tools atau observability stack?",
            {"dimension": "experience"},
        ),
        question_row(
            "data-analyst",
            8,
            "profile",
            "Sebutkan bahasa pemrograman favorit untuk analisis data dan alasannya.",
            {"dimension": "tooling"},
        ),
        question_row(
            "data-analyst",
            9,
            "profile",
            "Apa KPI utama yang Anda prioritaskan untuk pilot micro-credential ini?",
            {"dimension": "priority"},
        ),
        question_row(
            "data-analyst",
            10,
            "profile",
            (
                "Bagikan cerita singkat saat Anda harus menjelaskan hasil "
                "AI ke stakeholder non-teknis."
            ),
            {"dimension": "communication"},
        ),
    ]

    question_table = sa.table(
        "question_templates",
        sa.column("role_slug", sa.String()),
        sa.column("sequence", sa.Integer()),
        sa.column("question_type", question_type_enum),
        sa.column("prompt", sa.Text()),
        sa.column("metadata", sa.JSON()),
    )
    op.bulk_insert(question_table, backend_questions + analyst_questions)


def downgrade() -> None:
    op.drop_table("assessment_responses")
    op.drop_table("assessment_question_snapshots")
    op.drop_table("assessments")
    op.drop_table("question_templates")
    op.drop_table("role_catalog")
    assessment_status_enum.drop(op.get_bind())
    question_type_enum.drop(op.get_bind())
