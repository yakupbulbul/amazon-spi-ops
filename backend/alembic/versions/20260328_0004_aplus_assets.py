"""add aplus assets

Revision ID: 20260328_0004
Revises: 20260328_0003
Create Date: 2026-03-28 00:40:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260328_0004"
down_revision = "20260328_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "aplus_assets",
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("asset_scope", sa.String(length=32), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("public_url", sa.String(length=1024), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_aplus_assets_asset_scope"), "aplus_assets", ["asset_scope"], unique=False)
    op.create_index(op.f("ix_aplus_assets_product_id"), "aplus_assets", ["product_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_aplus_assets_product_id"), table_name="aplus_assets")
    op.drop_index(op.f("ix_aplus_assets_asset_scope"), table_name="aplus_assets")
    op.drop_table("aplus_assets")
