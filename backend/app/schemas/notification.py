from __future__ import annotations

from pydantic import BaseModel


class SlackTestResponse(BaseModel):
    event_id: str
    notification_id: str
    status: str
    message: str
