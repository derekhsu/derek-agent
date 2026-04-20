"""Add compression fields to sessions and messages.

Revision ID: 0002_add_compression_fields
Revises: 0001_initial
Create Date: 2026-04-20 11:40:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0002_add_compression_fields"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add is_compressed to sessions table
    op.add_column(
        "sessions",
        sa.Column("is_compressed", sa.Boolean(), nullable=True, default=False)
    )

    # Add message_type to messages table
    op.add_column(
        "messages",
        sa.Column("message_type", sa.String(), nullable=True, default="message")
    )


def downgrade() -> None:
    # Remove message_type from messages
    op.drop_column("messages", "message_type")

    # Remove is_compressed from sessions
    op.drop_column("sessions", "is_compressed")
