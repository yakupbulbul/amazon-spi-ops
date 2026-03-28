"""initial ops schema

Revision ID: 20260328_0001
Revises: None
Create Date: 2026-03-28 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260328_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "products",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("asin", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("brand", sa.String(length=255), nullable=True),
        sa.Column("marketplace_id", sa.String(length=64), nullable=False),
        sa.Column("price_amount", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("price_currency", sa.String(length=8), nullable=True),
        sa.Column("low_stock_threshold", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asin"),
        sa.UniqueConstraint("sku"),
    )
    op.create_table(
        "inventory_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("available_quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reserved_quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("inbound_quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("alert_status", sa.String(length=32), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "inventory_alerts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("snapshot_id", sa.Uuid(), nullable=True),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("message", sa.String(length=512), nullable=False),
        sa.Column("is_resolved", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["snapshot_id"], ["inventory_snapshots.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "aplus_drafts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("brand_tone", sa.String(length=255), nullable=True),
        sa.Column("positioning", sa.String(length=512), nullable=True),
        sa.Column("draft_payload", sa.JSON(), nullable=False),
        sa.Column("validated_payload", sa.JSON(), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "aplus_publish_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("draft_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("external_submission_id", sa.String(length=255), nullable=True),
        sa.Column("error_message", sa.String(length=1024), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["draft_id"], ["aplus_drafts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "price_change_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("old_price_amount", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("new_price_amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("response_payload", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "stock_change_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("old_quantity", sa.Integer(), nullable=True),
        sa.Column("new_quantity", sa.Integer(), nullable=False),
        sa.Column("response_payload", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "event_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "slack_notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_log_id", sa.Uuid(), nullable=True),
        sa.Column("notification_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("channel_label", sa.String(length=255), nullable=True),
        sa.Column("message_preview", sa.String(length=1024), nullable=False),
        sa.Column("response_payload", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["event_log_id"], ["event_logs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "app_settings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("description", sa.String(length=512), nullable=True),
        sa.Column("updated_by_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )

    op.create_index("ix_inventory_snapshots_product_id", "inventory_snapshots", ["product_id"])
    op.create_index("ix_inventory_alerts_product_id", "inventory_alerts", ["product_id"])
    op.create_index("ix_aplus_drafts_product_id", "aplus_drafts", ["product_id"])
    op.create_index("ix_price_change_logs_product_id", "price_change_logs", ["product_id"])
    op.create_index("ix_stock_change_logs_product_id", "stock_change_logs", ["product_id"])
    op.create_index("ix_event_logs_event_type", "event_logs", ["event_type"])
    op.create_index("ix_slack_notifications_status", "slack_notifications", ["status"])


def downgrade() -> None:
    op.drop_index("ix_slack_notifications_status", table_name="slack_notifications")
    op.drop_index("ix_event_logs_event_type", table_name="event_logs")
    op.drop_index("ix_stock_change_logs_product_id", table_name="stock_change_logs")
    op.drop_index("ix_price_change_logs_product_id", table_name="price_change_logs")
    op.drop_index("ix_aplus_drafts_product_id", table_name="aplus_drafts")
    op.drop_index("ix_inventory_alerts_product_id", table_name="inventory_alerts")
    op.drop_index("ix_inventory_snapshots_product_id", table_name="inventory_snapshots")
    op.drop_table("app_settings")
    op.drop_table("slack_notifications")
    op.drop_table("event_logs")
    op.drop_table("stock_change_logs")
    op.drop_table("price_change_logs")
    op.drop_table("aplus_publish_jobs")
    op.drop_table("aplus_drafts")
    op.drop_table("inventory_alerts")
    op.drop_table("inventory_snapshots")
    op.drop_table("products")
    op.drop_table("users")

