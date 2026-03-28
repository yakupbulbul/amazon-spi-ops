"""add aplus language metadata

Revision ID: 20260328_0003
Revises: 20260328_0002
Create Date: 2026-03-28 00:03:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260328_0003"
down_revision = "20260328_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "aplus_drafts",
        sa.Column("source_language", sa.String(length=16), nullable=False, server_default="de-DE"),
    )
    op.add_column(
        "aplus_drafts",
        sa.Column("target_language", sa.String(length=16), nullable=False, server_default="de-DE"),
    )
    op.add_column(
        "aplus_drafts",
        sa.Column("auto_translate", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("aplus_drafts", "source_language", server_default=None)
    op.alter_column("aplus_drafts", "target_language", server_default=None)
    op.alter_column("aplus_drafts", "auto_translate", server_default=None)


def downgrade() -> None:
    op.drop_column("aplus_drafts", "auto_translate")
    op.drop_column("aplus_drafts", "target_language")
    op.drop_column("aplus_drafts", "source_language")
