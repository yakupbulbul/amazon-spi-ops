from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel


class ProductInventorySummaryResponse(BaseModel):
    available_quantity: int
    reserved_quantity: int
    inbound_quantity: int
    alert_status: str


class ProductListItemResponse(BaseModel):
    id: str
    sku: str
    asin: str
    title: str
    brand: str | None
    marketplace_id: str
    price_amount: Decimal | None
    price_currency: str | None
    low_stock_threshold: int
    is_active: bool
    inventory: ProductInventorySummaryResponse | None


class ProductListResponse(BaseModel):
    items: list[ProductListItemResponse]
