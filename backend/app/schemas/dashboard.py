from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class DashboardMetricResponse(BaseModel):
    label: str
    value: int
    note: str


class ActivityItemResponse(BaseModel):
    title: str
    detail: str
    occurred_at: datetime


class AlertItemResponse(BaseModel):
    title: str
    detail: str
    severity: str
    occurred_at: datetime


class SlackStatusItemResponse(BaseModel):
    notification_type: str
    status: str
    message_preview: str
    created_at: datetime


class DashboardSummaryResponse(BaseModel):
    metrics: list[DashboardMetricResponse]
    recent_activity: list[ActivityItemResponse]
    inventory_alerts: list[AlertItemResponse]
    slack_delivery: list[SlackStatusItemResponse]

