from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user, get_notification_service
from app.models.entities import User
from app.schemas.event import EventListResponse
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=EventListResponse)
def read_events(
    _: User = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
) -> EventListResponse:
    return notification_service.list_events()
