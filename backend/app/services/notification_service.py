from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.entities import EventLog, SlackNotification, User
from app.models.enums import JobStatus
from app.schemas.event import EventListResponse, EventLogResponse, SlackNotificationLogResponse
from app.schemas.notification import SlackTestResponse
from app.services.slack_service import SlackWebhookService


class NotificationService:
    def __init__(
        self,
        db_session: Session,
        slack_service: SlackWebhookService | None = None,
    ) -> None:
        self.db_session = db_session
        self.slack_service = slack_service or SlackWebhookService()

    def list_events(self, *, limit: int = 50) -> EventListResponse:
        events = self.db_session.execute(
            select(EventLog)
            .options(selectinload(EventLog.slack_notifications))
            .order_by(EventLog.occurred_at.desc())
            .limit(limit)
        ).scalars().all()

        return EventListResponse(items=[self._serialize_event(event) for event in events])

    def send_test_notification(self, *, requested_by: User) -> SlackTestResponse:
        notification = self.queue_event_notification(
            event_type="slack_test",
            source="settings_ui",
            event_status=JobStatus.SUCCEEDED.value,
            event_payload={
                "requested_by": requested_by.email,
                "message": "Slack test notification queued from dashboard settings.",
            },
            notification_type="slack_test",
            message_preview=f"Slack test notification requested by {requested_by.email}.",
        )
        self.db_session.commit()
        self.dispatch_notification(notification.id)

        return SlackTestResponse(
            event_id=str(notification.event_log_id),
            notification_id=str(notification.id),
            status=JobStatus.PENDING.value,
            message="Slack test notification queued for background delivery.",
        )

    def queue_event_notification(
        self,
        *,
        event_type: str,
        source: str,
        event_status: str,
        event_payload: dict[str, object],
        notification_type: str,
        message_preview: str,
        occurred_at: datetime | None = None,
    ) -> SlackNotification:
        timestamp = occurred_at or self._now()
        event = EventLog(
            event_type=event_type,
            source=source,
            status=event_status,
            payload=event_payload,
            occurred_at=timestamp,
        )
        self.db_session.add(event)
        self.db_session.flush()

        notification = SlackNotification(
            event_log_id=event.id,
            notification_type=notification_type,
            status=JobStatus.PENDING.value,
            channel_label="incoming-webhook",
            message_preview=message_preview[:1024],
            created_at=timestamp,
        )
        self.db_session.add(notification)
        self.db_session.flush()
        return notification

    def deliver_slack_notification(self, notification_id: UUID) -> None:
        notification = self.db_session.get(SlackNotification, notification_id)
        if notification is None:
            return

        event = notification.event_log
        if event is None:
            notification.status = JobStatus.FAILED.value
            notification.error_message = "Related event log is missing."
            self.db_session.commit()
            return

        text, blocks = self._build_slack_message(event=event, notification=notification)

        try:
            response_payload = self.slack_service.send_message(text=text, blocks=blocks)
            notification.status = JobStatus.SUCCEEDED.value
            notification.response_payload = response_payload
            notification.error_message = None
        except Exception as exc:
            notification.status = JobStatus.FAILED.value
            notification.error_message = str(exc)[:1024]

        self.db_session.commit()

    @staticmethod
    def dispatch_notification(notification_id: UUID) -> None:
        from app.workers.main import dispatch_slack_notification

        dispatch_slack_notification.send(str(notification_id))

    def _build_slack_message(
        self,
        *,
        event: EventLog,
        notification: SlackNotification,
    ) -> tuple[str, list[dict[str, Any]]]:
        summary = notification.message_preview
        payload_preview = self._format_payload_preview(event.payload)
        blocks: list[dict[str, Any]] = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{summary}*",
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": (
                            f"event: `{event.event_type}`  "
                            f"source: `{event.source}`  "
                            f"status: `{event.status}`"
                        ),
                    }
                ],
            },
        ]

        if payload_preview:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"```{payload_preview}```",
                    },
                }
            )

        return summary, blocks

    @staticmethod
    def _format_payload_preview(payload: dict[str, object]) -> str:
        compact_items = []
        for key, value in payload.items():
            compact_items.append(f"{key}: {value}")
        preview = " | ".join(compact_items)
        return preview[:900]

    @staticmethod
    def _serialize_event(event: EventLog) -> EventLogResponse:
        notifications = sorted(
            event.slack_notifications,
            key=lambda item: item.created_at,
            reverse=True,
        )
        return EventLogResponse(
            id=str(event.id),
            event_type=event.event_type,
            source=event.source,
            status=event.status,
            payload=event.payload,
            occurred_at=event.occurred_at,
            notifications=[
                SlackNotificationLogResponse(
                    id=str(notification.id),
                    notification_type=notification.notification_type,
                    status=notification.status,
                    channel_label=notification.channel_label,
                    message_preview=notification.message_preview,
                    error_message=notification.error_message,
                    created_at=notification.created_at,
                )
                for notification in notifications
            ],
        )

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)
