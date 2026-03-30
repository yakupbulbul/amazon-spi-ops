from __future__ import annotations

from pydantic import BaseModel, Field


class SlackTestResponse(BaseModel):
    event_id: str
    notification_id: str
    status: str
    message: str


class OrderNotificationRequest(BaseModel):
    marketplace_id: str
    order_id: str
    sku: str
    asin: str
    quantity: int = Field(ge=1)
    status: str = 'new'
    product_title: str | None = None


class OrderNotificationResponse(BaseModel):
    event_id: str
    notification_id: str
    status: str
    message: str
