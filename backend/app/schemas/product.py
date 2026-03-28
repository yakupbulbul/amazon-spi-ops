from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


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
    source: str
    marketplace_id: str
    price_amount: Decimal | None
    price_currency: str | None
    low_stock_threshold: int
    is_active: bool
    inventory: ProductInventorySummaryResponse | None


class ProductListResponse(BaseModel):
    items: list[ProductListItemResponse]


class ProductPriceUpdateRequest(BaseModel):
    price_amount: Decimal = Field(gt=Decimal("0"))
    price_currency: str = Field(min_length=3, max_length=8)


class ProductStockUpdateRequest(BaseModel):
    quantity: int = Field(ge=0)


class ProductMutationResponse(BaseModel):
    product_id: str
    status: str
    message: str
    updated_at: datetime


class CatalogImportJobResponse(BaseModel):
    id: str
    status: str
    source: str
    marketplace_id: str
    created_count: int
    updated_count: int
    skipped_count: int
    error_count: int
    processed_count: int
    total_expected: int | None
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    created_at: datetime
