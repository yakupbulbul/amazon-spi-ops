from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user, get_notification_service
from app.models.entities import User
from app.schemas.notification import SlackTestResponse
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("/slack/test", response_model=SlackTestResponse)
def send_slack_test_notification(
    current_user: User = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
) -> SlackTestResponse:
    return notification_service.send_test_notification(requested_by=current_user)
