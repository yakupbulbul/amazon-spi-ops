from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, aliased

from app.models.entities import (
    InventoryAlert,
    InventorySnapshot,
    PriceChangeLog,
    Product,
    StockChangeLog,
    User,
)
from app.models.enums import AlertSeverity, InventoryAlertStatus, JobStatus
from app.schemas.product import (
    CatalogImportJobResponse,
    ProductInventorySummaryResponse,
    ProductListItemResponse,
    ProductListResponse,
    ProductMutationResponse,
)
from app.services.amazon.service import AmazonSpApiService
from app.services.catalog_import_service import CatalogImportService
from app.services.notification_service import NotificationService


class ProductService:
    def __init__(self, db_session: Session, amazon_service: AmazonSpApiService) -> None:
        self.db_session = db_session
        self.amazon_service = amazon_service

    def list_products(self) -> ProductListResponse:
        latest_snapshot = (
            select(
                InventorySnapshot.product_id.label("product_id"),
                func.max(InventorySnapshot.captured_at).label("captured_at"),
            )
            .group_by(InventorySnapshot.product_id)
            .subquery()
        )
        snapshot_alias = aliased(InventorySnapshot)
        statement: Select[tuple[Product, InventorySnapshot | None]] = (
            select(Product, snapshot_alias)
            .outerjoin(latest_snapshot, latest_snapshot.c.product_id == Product.id)
            .outerjoin(
                snapshot_alias,
                (snapshot_alias.product_id == latest_snapshot.c.product_id)
                & (snapshot_alias.captured_at == latest_snapshot.c.captured_at),
            )
            .order_by(Product.title.asc())
        )
        rows = self.db_session.execute(statement).all()

        return ProductListResponse(
            items=[
                ProductListItemResponse(
                    id=str(product.id),
                    sku=product.sku,
                    asin=product.asin,
                    title=product.title,
                    brand=product.brand,
                    source=product.source,
                    marketplace_id=product.marketplace_id,
                    price_amount=product.price_amount,
                    price_currency=product.price_currency,
                    low_stock_threshold=product.low_stock_threshold,
                    is_active=product.is_active,
                    inventory=(
                        ProductInventorySummaryResponse(
                            available_quantity=snapshot.available_quantity,
                            reserved_quantity=snapshot.reserved_quantity,
                            inbound_quantity=snapshot.inbound_quantity,
                            alert_status=snapshot.alert_status,
                        )
                        if snapshot is not None
                        else None
                    ),
                )
                for product, snapshot in rows
            ]
        )

    def create_import_job(self, *, requested_by: User) -> CatalogImportJobResponse:
        return CatalogImportService(self.db_session, self.amazon_service).create_import_job(
            created_by=requested_by
        )

    def get_latest_import_job(self) -> CatalogImportJobResponse | None:
        return CatalogImportService(self.db_session, self.amazon_service).get_latest_job()

    def update_price(
        self,
        *,
        product_id: UUID,
        price_amount: Decimal,
        price_currency: str,
        requested_by: User,
    ) -> ProductMutationResponse:
        product = self._get_product(product_id)
        old_price_amount = product.price_amount
        timestamp = self._now()
        notification_service = NotificationService(self.db_session)

        try:
            response_payload = self.amazon_service.update_listing_price(
                sku=product.sku,
                price=price_amount,
                currency=price_currency.upper(),
                marketplace_id=product.marketplace_id,
            )
            product.price_amount = price_amount
            product.price_currency = price_currency.upper()
            change_log = PriceChangeLog(
                product_id=product.id,
                requested_by_id=requested_by.id,
                status=JobStatus.SUCCEEDED.value,
                old_price_amount=old_price_amount,
                new_price_amount=price_amount,
                currency=price_currency.upper(),
                response_payload=response_payload,
                created_at=timestamp,
            )
            self.db_session.add(change_log)
            notification = notification_service.queue_event_notification(
                event_type="price_update",
                source="products_api",
                event_status=JobStatus.SUCCEEDED.value,
                event_payload={
                    "sku": product.sku,
                    "asin": product.asin,
                    "old_price_amount": str(old_price_amount) if old_price_amount is not None else None,
                    "new_price_amount": str(price_amount),
                    "currency": price_currency.upper(),
                },
                notification_type="price_update_success",
                message_preview=(
                    f"Price update succeeded for {product.sku}: "
                    f"{price_currency.upper()} {price_amount}."
                ),
                occurred_at=timestamp,
            )
            self.db_session.commit()
            notification_service.dispatch_notification(notification.id)
            return ProductMutationResponse(
                product_id=str(product.id),
                status=JobStatus.SUCCEEDED.value,
                message=f"Updated {product.sku} price to {price_currency.upper()} {price_amount}.",
                updated_at=timestamp,
            )
        except Exception as exc:
            self.db_session.add(
                PriceChangeLog(
                    product_id=product.id,
                    requested_by_id=requested_by.id,
                    status=JobStatus.FAILED.value,
                    old_price_amount=old_price_amount,
                    new_price_amount=price_amount,
                    currency=price_currency.upper(),
                    error_message=str(exc),
                    created_at=timestamp,
                )
            )
            notification = notification_service.queue_event_notification(
                event_type="price_update",
                source="products_api",
                event_status=JobStatus.FAILED.value,
                event_payload={
                    "sku": product.sku,
                    "asin": product.asin,
                    "attempted_price_amount": str(price_amount),
                    "currency": price_currency.upper(),
                    "error": str(exc),
                },
                notification_type="price_update_failure",
                message_preview=f"Price update failed for {product.sku}.",
                occurred_at=timestamp,
            )
            self.db_session.commit()
            notification_service.dispatch_notification(notification.id)
            raise

    def update_stock(
        self,
        *,
        product_id: UUID,
        quantity: int,
        requested_by: User,
    ) -> ProductMutationResponse:
        product = self._get_product(product_id)
        latest_snapshot = self.db_session.execute(
            select(InventorySnapshot)
            .where(InventorySnapshot.product_id == product.id)
            .order_by(InventorySnapshot.captured_at.desc())
            .limit(1)
        ).scalar_one_or_none()
        reserved_quantity = latest_snapshot.reserved_quantity if latest_snapshot else 0
        inbound_quantity = latest_snapshot.inbound_quantity if latest_snapshot else 0
        old_quantity = latest_snapshot.available_quantity if latest_snapshot else None
        timestamp = self._now()
        notification_service = NotificationService(self.db_session)

        try:
            response_payload = self.amazon_service.update_listing_stock(
                sku=product.sku,
                quantity=quantity,
                marketplace_id=product.marketplace_id,
            )
            snapshot = InventorySnapshot(
                product_id=product.id,
                available_quantity=quantity,
                reserved_quantity=reserved_quantity,
                inbound_quantity=inbound_quantity,
                alert_status=self._determine_alert_status(
                    available_quantity=quantity,
                    threshold=product.low_stock_threshold,
                ),
                captured_at=timestamp,
            )
            self.db_session.add(snapshot)
            self.db_session.flush()
            notification_ids: list[UUID] = []
            alert = self._reconcile_alert(product=product, snapshot=snapshot)
            if alert is not None:
                alert_notification = notification_service.queue_event_notification(
                    event_type="inventory_alert",
                    source="products_api",
                    event_status=alert.severity,
                    event_payload={
                        "sku": product.sku,
                        "asin": product.asin,
                        "available_quantity": quantity,
                        "threshold": product.low_stock_threshold,
                        "message": alert.message,
                    },
                    notification_type="low_stock_threshold_reached",
                    message_preview=alert.message,
                    occurred_at=timestamp,
                )
                notification_ids.append(alert_notification.id)
            self.db_session.add(
                StockChangeLog(
                    product_id=product.id,
                    requested_by_id=requested_by.id,
                    status=JobStatus.SUCCEEDED.value,
                    old_quantity=old_quantity,
                    new_quantity=quantity,
                    response_payload=response_payload,
                    created_at=timestamp,
                )
            )
            stock_notification = notification_service.queue_event_notification(
                event_type="stock_update",
                source="products_api",
                event_status=JobStatus.SUCCEEDED.value,
                event_payload={
                    "sku": product.sku,
                    "asin": product.asin,
                    "old_quantity": old_quantity,
                    "new_quantity": quantity,
                },
                notification_type="stock_update_success",
                message_preview=f"Stock update succeeded for {product.sku}: quantity {quantity}.",
                occurred_at=timestamp,
            )
            notification_ids.append(stock_notification.id)
            self.db_session.commit()
            for notification_id in notification_ids:
                notification_service.dispatch_notification(notification_id)
            return ProductMutationResponse(
                product_id=str(product.id),
                status=JobStatus.SUCCEEDED.value,
                message=f"Updated {product.sku} stock to {quantity}.",
                updated_at=timestamp,
            )
        except Exception as exc:
            self.db_session.add(
                StockChangeLog(
                    product_id=product.id,
                    requested_by_id=requested_by.id,
                    status=JobStatus.FAILED.value,
                    old_quantity=old_quantity,
                    new_quantity=quantity,
                    error_message=str(exc),
                    created_at=timestamp,
                )
            )
            notification = notification_service.queue_event_notification(
                event_type="stock_update",
                source="products_api",
                event_status=JobStatus.FAILED.value,
                event_payload={
                    "sku": product.sku,
                    "asin": product.asin,
                    "attempted_quantity": quantity,
                    "error": str(exc),
                },
                notification_type="stock_update_failure",
                message_preview=f"Stock update failed for {product.sku}.",
                occurred_at=timestamp,
            )
            self.db_session.commit()
            notification_service.dispatch_notification(notification.id)
            raise

    def _get_product(self, product_id: UUID) -> Product:
        product = self.db_session.get(Product, product_id)
        if product is None:
            raise ValueError("Product not found.")
        return product

    def _reconcile_alert(
        self,
        *,
        product: Product,
        snapshot: InventorySnapshot,
    ) -> InventoryAlert | None:
        unresolved_alerts = self.db_session.execute(
            select(InventoryAlert)
            .where(
                InventoryAlert.product_id == product.id,
                InventoryAlert.is_resolved.is_(False),
            )
            .order_by(InventoryAlert.created_at.desc())
        ).scalars().all()

        if snapshot.alert_status == InventoryAlertStatus.HEALTHY.value:
            for alert in unresolved_alerts:
                alert.is_resolved = True
                alert.resolved_at = self._now()
            return None

        for alert in unresolved_alerts:
            alert.is_resolved = True
            alert.resolved_at = self._now()

        severity = (
            AlertSeverity.CRITICAL.value
            if snapshot.alert_status == InventoryAlertStatus.OUT_OF_STOCK.value
            else AlertSeverity.WARNING.value
        )
        message = (
            f"{product.sku} is out of stock."
            if snapshot.alert_status == InventoryAlertStatus.OUT_OF_STOCK.value
            else f"{product.sku} is at or below the low-stock threshold."
        )
        alert = InventoryAlert(
            product_id=product.id,
            snapshot_id=snapshot.id,
            severity=severity,
            message=message,
            is_resolved=False,
            created_at=self._now(),
        )
        self.db_session.add(alert)
        self.db_session.flush()
        return alert

    @staticmethod
    def _determine_alert_status(*, available_quantity: int, threshold: int) -> str:
        if available_quantity <= 0:
            return InventoryAlertStatus.OUT_OF_STOCK.value
        if available_quantity <= threshold:
            return InventoryAlertStatus.LOW.value
        return InventoryAlertStatus.HEALTHY.value

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)
