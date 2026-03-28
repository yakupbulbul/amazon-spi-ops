from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class InventoryItemResponse(BaseModel):
    product_id: str
    sku: str
    asin: str
    product_name: str
    marketplace_id: str
    available_quantity: int
    reserved_quantity: int
    inbound_quantity: int
    low_stock_threshold: int
    alert_status: str
    captured_at: datetime | None


class InventoryListResponse(BaseModel):
    items: list[InventoryItemResponse]


class InventoryAlertResponse(BaseModel):
    product_id: str
    sku: str
    product_name: str
    severity: str
    message: str
    available_quantity: int
    low_stock_threshold: int
    created_at: datetime


class InventoryAlertListResponse(BaseModel):
    items: list[InventoryAlertResponse]


class InventorySyncResponse(BaseModel):
    status: str
    source: str
    synced_count: int
    synced_at: datetime
