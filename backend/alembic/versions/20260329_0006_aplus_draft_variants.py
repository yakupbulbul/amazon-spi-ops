"""add aplus draft variants

Revision ID: 20260329_0006
Revises: 20260329_0005
Create Date: 2026-03-29 21:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260329_0006"
down_revision = "20260329_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "aplus_drafts",
        sa.Column("variant_group_id", sa.String(length=36), nullable=True),
    )
    op.add_column(
        "aplus_drafts",
        sa.Column("variant_role", sa.String(length=16), nullable=True),
    )
    op.create_index(
        op.f("ix_aplus_drafts_variant_group_id"),
        "aplus_drafts",
        ["variant_group_id"],
        unique=False,
    )

    op.execute("UPDATE aplus_drafts SET variant_group_id = id::text WHERE variant_group_id IS NULL")
    op.execute(
        "UPDATE aplus_drafts SET variant_role = CASE WHEN auto_translate THEN 'translated' ELSE 'original' END WHERE variant_role IS NULL"
    )

    op.alter_column("aplus_drafts", "variant_group_id", nullable=False)
    op.alter_column("aplus_drafts", "variant_role", nullable=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_aplus_drafts_variant_group_id"), table_name="aplus_drafts")
    op.drop_column("aplus_drafts", "variant_role")
    op.drop_column("aplus_drafts", "variant_group_id")
