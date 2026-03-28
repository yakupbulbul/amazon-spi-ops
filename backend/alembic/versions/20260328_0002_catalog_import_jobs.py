"""add catalog import jobs and product source

Revision ID: 20260328_0002
Revises: 20260328_0001
Create Date: 2026-03-28 00:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260328_0002"
down_revision = "20260328_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column("source", sa.String(length=32), nullable=False, server_default="sample"),
    )
    op.create_index("ix_products_source", "products", ["source"])

    op.create_table(
        "catalog_import_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("source", sa.String(length=64), nullable=False, server_default="amazon_sp_api"),
        sa.Column("marketplace_id", sa.String(length=64), nullable=False),
        sa.Column("created_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_expected", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.String(length=1024), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_catalog_import_jobs_marketplace_id", "catalog_import_jobs", ["marketplace_id"])
    op.create_index("ix_catalog_import_jobs_status", "catalog_import_jobs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_catalog_import_jobs_status", table_name="catalog_import_jobs")
    op.drop_index("ix_catalog_import_jobs_marketplace_id", table_name="catalog_import_jobs")
    op.drop_table("catalog_import_jobs")
    op.drop_index("ix_products_source", table_name="products")
    op.drop_column("products", "source")
