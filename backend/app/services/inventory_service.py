from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, aliased

from app.models.entities import InventoryAlert, InventorySnapshot, Product
from app.models.enums import AlertSeverity, InventoryAlertStatus
from app.schemas.inventory import (
    InventoryAlertListResponse,
    InventoryAlertResponse,
    InventoryItemResponse,
    InventoryListResponse,
    InventorySyncResponse,
)
from app.services.amazon.service import AmazonSpApiService
from app.services.notification_service import NotificationService


class InventoryService:
    def __init__(self, db_session: Session, amazon_service: AmazonSpApiService) -> None:
        self.db_session = db_session
        self.amazon_service = amazon_service

    def list_inventory(self) -> InventoryListResponse:
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

        return InventoryListResponse(
            items=[
                InventoryItemResponse(
                    product_id=str(product.id),
                    sku=product.sku,
                    asin=product.asin,
                    product_name=product.title,
                    marketplace_id=product.marketplace_id,
                    available_quantity=snapshot.available_quantity if snapshot else 0,
                    reserved_quantity=snapshot.reserved_quantity if snapshot else 0,
                    inbound_quantity=snapshot.inbound_quantity if snapshot else 0,
                    low_stock_threshold=product.low_stock_threshold,
                    alert_status=snapshot.alert_status if snapshot else InventoryAlertStatus.HEALTHY.value,
                    captured_at=snapshot.captured_at if snapshot else None,
                )
                for product, snapshot in rows
            ]
        )

    def list_alerts(self) -> InventoryAlertListResponse:
        rows = self.db_session.execute(
            select(InventoryAlert, Product, InventorySnapshot)
            .join(Product, Product.id == InventoryAlert.product_id)
            .outerjoin(InventorySnapshot, InventorySnapshot.id == InventoryAlert.snapshot_id)
            .where(InventoryAlert.is_resolved.is_(False))
            .order_by(InventoryAlert.created_at.desc())
        ).all()

        return InventoryAlertListResponse(
            items=[
                InventoryAlertResponse(
                    product_id=str(product.id),
                    sku=product.sku,
                    product_name=product.title,
                    severity=alert.severity,
                    message=alert.message,
                    available_quantity=snapshot.available_quantity if snapshot else 0,
                    low_stock_threshold=product.low_stock_threshold,
                    created_at=alert.created_at,
                )
                for alert, product, snapshot in rows
            ]
        )

    def sync_inventory(self) -> InventorySyncResponse:
        products = self.db_session.execute(select(Product).order_by(Product.title.asc())).scalars().all()
        if not products:
            return InventorySyncResponse(
                status="idle",
                source="local",
                synced_count=0,
                synced_at=self._now(),
            )

        target_marketplace = self.amazon_service.settings.marketplace_id or products[0].marketplace_id
        response = self.amazon_service.get_inventory_summaries(
            marketplace_id=target_marketplace,
        )
        response_summaries = self._normalize_response_summaries(response)
        self._upsert_products_from_response(
            response_summaries=response_summaries,
            marketplace_id=target_marketplace,
        )

        products = self.db_session.execute(
            select(Product)
            .where(Product.marketplace_id == target_marketplace)
            .order_by(Product.title.asc())
        ).scalars().all()
        preserve_missing_snapshot = bool(response.get("mock"))
        notification_service = NotificationService(self.db_session)
        notification_ids: list[UUID] = []

        synced_count = 0
        for product in products:
            summary = response_summaries.get(product.sku)
            latest_snapshot = self.db_session.execute(
                select(InventorySnapshot)
                .where(InventorySnapshot.product_id == product.id)
                .order_by(InventorySnapshot.captured_at.desc())
                .limit(1)
            ).scalar_one_or_none()

            available_quantity = (
                summary["available_quantity"]
                if summary
                else latest_snapshot.available_quantity if preserve_missing_snapshot and latest_snapshot else 0
            )
            reserved_quantity = (
                summary["reserved_quantity"]
                if summary
                else latest_snapshot.reserved_quantity if preserve_missing_snapshot and latest_snapshot else 0
            )
            inbound_quantity = (
                summary["inbound_quantity"]
                if summary
                else latest_snapshot.inbound_quantity if preserve_missing_snapshot and latest_snapshot else 0
            )

            snapshot = InventorySnapshot(
                product_id=product.id,
                available_quantity=available_quantity,
                reserved_quantity=reserved_quantity,
                inbound_quantity=inbound_quantity,
                alert_status=self._determine_alert_status(
                    available_quantity=available_quantity,
                    threshold=product.low_stock_threshold,
                ),
                captured_at=self._now(),
            )
            self.db_session.add(snapshot)
            self.db_session.flush()
            alert = self._reconcile_alert(product=product, snapshot=snapshot)
            if alert is not None:
                notification = notification_service.queue_event_notification(
                    event_type="inventory_alert",
                    source="inventory_sync",
                    event_status=alert.severity,
                    event_payload={
                        "marketplace_id": product.marketplace_id,
                        "sku": product.sku,
                        "asin": product.asin,
                        "available_quantity": available_quantity,
                        "threshold": product.low_stock_threshold,
                        "stock_health": snapshot.alert_status,
                        "message": alert.message,
                    },
                    notification_type="low_stock_threshold_reached",
                    message_preview=alert.message,
                    occurred_at=snapshot.captured_at,
                )
                notification_ids.append(notification.id)
            synced_count += 1

        self.db_session.commit()
        for notification_id in notification_ids:
            notification_service.dispatch_notification(notification_id)
        return InventorySyncResponse(
            status="completed",
            source="amazon_mock" if response.get("mock") else "amazon_live",
            synced_count=synced_count,
            synced_at=self._now(),
        )

    def _normalize_response_summaries(self, response: dict[str, object]) -> dict[str, dict[str, object]]:
        summaries = response.get("summaries")
        if isinstance(summaries, list):
            normalized: dict[str, dict[str, object]] = {}
            for item in summaries:
                if not isinstance(item, dict):
                    continue
                sku = item.get("seller_sku")
                if not isinstance(sku, str):
                    continue
                normalized[sku] = {
                    "available_quantity": int(item.get("available_quantity", 0)),
                    "reserved_quantity": int(item.get("reserved_quantity", 0)),
                    "inbound_quantity": int(item.get("inbound_quantity", 0)),
                    "asin": item.get("asin"),
                    "product_name": item.get("product_name"),
                }
            return normalized

        inventory_summaries = response.get("inventorySummaries")
        if not isinstance(inventory_summaries, list):
            return {}

        normalized = {}
        for item in inventory_summaries:
            if not isinstance(item, dict):
                continue
            sku = item.get("sellerSku")
            if not isinstance(sku, str):
                continue
            total_reserved_quantity = item.get("totalReservedQuantity", item.get("reservedQuantity", 0))
            available_quantity = item.get("fulfillableQuantity", item.get("totalQuantity", 0))
            normalized[sku] = {
                "available_quantity": int(available_quantity or 0),
                "reserved_quantity": int(total_reserved_quantity or 0),
                "inbound_quantity": int(item.get("inboundWorkingQuantity", 0)),
                "asin": item.get("asin"),
                "product_name": item.get("productName"),
            }
        return normalized

    def _upsert_products_from_response(
        self,
        *,
        response_summaries: dict[str, dict[str, object]],
        marketplace_id: str,
    ) -> None:
        if not response_summaries:
            return

        existing_products = self.db_session.execute(select(Product)).scalars().all()
        products_by_sku = {product.sku: product for product in existing_products}

        for sku, summary in response_summaries.items():
            if sku in products_by_sku:
                product = products_by_sku[sku]
                if product.marketplace_id != marketplace_id:
                    product.marketplace_id = marketplace_id
                continue

            asin = summary.get("asin")
            if not isinstance(asin, str) or not asin:
                continue

            product_name = summary.get("product_name")
            title = product_name if isinstance(product_name, str) and product_name else sku
            self.db_session.add(
                Product(
                    sku=sku,
                    asin=asin,
                    title=title,
                    marketplace_id=marketplace_id,
                    price_amount=Decimal("0.00"),
                    price_currency=None,
                    low_stock_threshold=10,
                    is_active=True,
                )
            )

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
