from __future__ import annotations

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, aliased

from app.models.entities import InventorySnapshot, Product
from app.schemas.product import (
    ProductInventorySummaryResponse,
    ProductListItemResponse,
    ProductListResponse,
)


class ProductService:
    def __init__(self, db_session: Session) -> None:
        self.db_session = db_session

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
