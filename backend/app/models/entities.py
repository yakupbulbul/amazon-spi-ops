from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import (
    AlertSeverity,
    CatalogImportStatus,
    DraftStatus,
    InventoryAlertStatus,
    JobStatus,
    ProductSource,
    UserRole,
)
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default=UserRole.ADMIN.value, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Product(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "products"

    sku: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    asin: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(255))
    source: Mapped[str] = mapped_column(
        String(32), default=ProductSource.SAMPLE.value, nullable=False, index=True
    )
    marketplace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    price_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    price_currency: Mapped[str | None] = mapped_column(String(8))
    low_stock_threshold: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    inventory_snapshots: Mapped[list["InventorySnapshot"]] = relationship(back_populates="product")
    inventory_alerts: Mapped[list["InventoryAlert"]] = relationship(back_populates="product")
    aplus_drafts: Mapped[list["AplusDraft"]] = relationship(back_populates="product")
    price_change_logs: Mapped[list["PriceChangeLog"]] = relationship(back_populates="product")
    stock_change_logs: Mapped[list["StockChangeLog"]] = relationship(back_populates="product")


class InventorySnapshot(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "inventory_snapshots"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    available_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reserved_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    inbound_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    alert_status: Mapped[str] = mapped_column(
        String(32), default=InventoryAlertStatus.HEALTHY.value, nullable=False
    )
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    product: Mapped[Product] = relationship(back_populates="inventory_snapshots")


class InventoryAlert(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "inventory_alerts"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inventory_snapshots.id", ondelete="SET NULL")
    )
    severity: Mapped[str] = mapped_column(String(32), default=AlertSeverity.WARNING.value, nullable=False)
    message: Mapped[str] = mapped_column(String(512), nullable=False)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    product: Mapped[Product] = relationship(back_populates="inventory_alerts")
    snapshot: Mapped[InventorySnapshot | None] = relationship()


class AplusDraft(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "aplus_drafts"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(32), default=DraftStatus.DRAFT.value, nullable=False)
    brand_tone: Mapped[str | None] = mapped_column(String(255))
    positioning: Mapped[str | None] = mapped_column(String(512))
    draft_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    validated_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )

    product: Mapped[Product] = relationship(back_populates="aplus_drafts")
    created_by: Mapped[User | None] = relationship()
    publish_jobs: Mapped[list["AplusPublishJob"]] = relationship(back_populates="draft")


class AplusPublishJob(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "aplus_publish_jobs"

    draft_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("aplus_drafts.id", ondelete="CASCADE")
    )
    status: Mapped[str] = mapped_column(String(32), default=JobStatus.PENDING.value, nullable=False)
    external_submission_id: Mapped[str | None] = mapped_column(String(255))
    error_message: Mapped[str | None] = mapped_column(String(1024))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    draft: Mapped[AplusDraft] = relationship(back_populates="publish_jobs")


class PriceChangeLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "price_change_logs"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    requested_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(String(32), default=JobStatus.PENDING.value, nullable=False)
    old_price_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    new_price_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    response_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error_message: Mapped[str | None] = mapped_column(String(1024))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    product: Mapped[Product] = relationship(back_populates="price_change_logs")
    requested_by: Mapped[User | None] = relationship()


class StockChangeLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "stock_change_logs"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    requested_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(String(32), default=JobStatus.PENDING.value, nullable=False)
    old_quantity: Mapped[int | None] = mapped_column(Integer)
    new_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    response_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error_message: Mapped[str | None] = mapped_column(String(1024))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    product: Mapped[Product] = relationship(back_populates="stock_change_logs")
    requested_by: Mapped[User | None] = relationship()


class EventLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "event_logs"

    event_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=JobStatus.PENDING.value, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    slack_notifications: Mapped[list["SlackNotification"]] = relationship(back_populates="event_log")


class SlackNotification(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "slack_notifications"

    event_log_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("event_logs.id", ondelete="SET NULL")
    )
    notification_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=JobStatus.PENDING.value, index=True)
    channel_label: Mapped[str | None] = mapped_column(String(255))
    message_preview: Mapped[str] = mapped_column(String(1024), nullable=False)
    response_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error_message: Mapped[str | None] = mapped_column(String(1024))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    event_log: Mapped[EventLog | None] = relationship(back_populates="slack_notifications")


class AppSetting(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    value: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    description: Mapped[str | None] = mapped_column(String(512))
    updated_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )

    updated_by: Mapped[User | None] = relationship()


class CatalogImportJob(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "catalog_import_jobs"

    status: Mapped[str] = mapped_column(
        String(32), default=CatalogImportStatus.PENDING.value, nullable=False, index=True
    )
    source: Mapped[str] = mapped_column(String(64), default="amazon_sp_api", nullable=False)
    marketplace_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_expected: Mapped[int | None] = mapped_column(Integer)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(String(1024))
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    created_by: Mapped[User | None] = relationship()
