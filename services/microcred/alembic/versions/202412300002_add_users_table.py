"""Add users table for authentication

Revision ID: 202412300002
Revises: 202412300001
Create Date: 2024-12-30 00:02:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "202412300002"
down_revision = "202412300001"
branch_labels = None
depends_on = None

user_role_enum = sa.Enum(
    "student",
    "advisor",
    "admin",
    name="user_role",
)

user_status_enum = sa.Enum(
    "active",
    "inactive",
    "suspended",
    name="user_status",
)


def upgrade() -> None:
    # Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=128), nullable=True),
        sa.Column("role", user_role_enum, nullable=False, server_default="student"),
        sa.Column("status", user_status_enum, nullable=False, server_default="active"),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Create index on email for faster lookups
    op.create_index("ix_users_email", "users", ["email"])


def downgrade() -> None:
    op.drop_index("ix_users_email", "users")
    op.drop_table("users")
    user_role_enum.drop(op.get_bind(), checkfirst=True)
    user_status_enum.drop(op.get_bind(), checkfirst=True)
