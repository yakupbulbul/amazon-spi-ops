from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SlackNotificationLogResponse(BaseModel):
    id: str
    notification_type: str
    status: str
    channel_label: str | None
    message_preview: str
    error_message: str | None
    created_at: datetime


class EventLogResponse(BaseModel):
    id: str
    event_type: str
    source: str
    status: str
    payload: dict[str, object]
    occurred_at: datetime
    notifications: list[SlackNotificationLogResponse]


class EventListResponse(BaseModel):
    items: list[EventLogResponse]
