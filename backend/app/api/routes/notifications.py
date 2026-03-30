from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user, get_notification_service
from app.models.entities import User
from app.schemas.notification import (
    OrderNotificationRequest,
    OrderNotificationResponse,
    SlackTestResponse,
)
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("/slack/test", response_model=SlackTestResponse)
def send_slack_test_notification(
    current_user: User = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
) -> SlackTestResponse:
    return notification_service.send_test_notification(requested_by=current_user)


@router.post("/orders/test", response_model=OrderNotificationResponse)
def send_order_test_notification(
    payload: OrderNotificationRequest,
    current_user: User = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
) -> OrderNotificationResponse:
    notification = notification_service.queue_new_order_notification(
        marketplace_id=payload.marketplace_id,
        order_id=payload.order_id,
        sku=payload.sku,
        asin=payload.asin,
        quantity=payload.quantity,
        status=payload.status,
        product_title=payload.product_title,
    )
    return OrderNotificationResponse(
        event_id=str(notification.event_log_id),
        notification_id=str(notification.id),
        status="pending",
        message=f"Order notification queued by {current_user.email}.",
    )
