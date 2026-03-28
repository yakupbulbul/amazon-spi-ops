from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.entities import (
    AplusDraft,
    EventLog,
    InventoryAlert,
    Product,
    SlackNotification,
)
from app.models.enums import DraftStatus, JobStatus
from app.schemas.dashboard import (
    ActivityItemResponse,
    AlertItemResponse,
    DashboardMetricResponse,
    DashboardSummaryResponse,
    SlackStatusItemResponse,
)


class DashboardService:
    def __init__(self, db_session: Session) -> None:
        self.db_session = db_session

    def get_summary(self) -> DashboardSummaryResponse:
        total_products = self.db_session.scalar(select(func.count(Product.id))) or 0
        low_stock_products = (
            self.db_session.scalar(
                select(func.count(func.distinct(InventoryAlert.product_id))).where(
                    InventoryAlert.is_resolved.is_(False)
                )
            )
            or 0
        )
        recent_sales_events = (
            self.db_session.scalar(
                select(func.count(EventLog.id)).where(EventLog.event_type == "sale")
            )
            or 0
        )
        pending_aplus_drafts = (
            self.db_session.scalar(
                select(func.count(AplusDraft.id)).where(
                    AplusDraft.status.in_(
                        [
                            DraftStatus.DRAFT.value,
                            DraftStatus.VALIDATED.value,
                            DraftStatus.READY_TO_PUBLISH.value,
                        ]
                    )
                )
            )
            or 0
        )

        recent_activity_rows = self.db_session.execute(
            select(EventLog).order_by(EventLog.occurred_at.desc()).limit(5)
        ).scalars()
        inventory_alert_rows = self.db_session.execute(
            select(InventoryAlert)
            .where(InventoryAlert.is_resolved.is_(False))
            .order_by(InventoryAlert.created_at.desc())
            .limit(5)
        ).scalars()
        slack_rows = self.db_session.execute(
            select(SlackNotification).order_by(SlackNotification.created_at.desc()).limit(5)
        ).scalars()

        metrics = [
            DashboardMetricResponse(
                label="Tracked products",
                value=total_products,
                note="Products in the local seller catalog mirror.",
            ),
            DashboardMetricResponse(
                label="Low stock products",
                value=low_stock_products,
                note="Distinct products with unresolved inventory alerts.",
            ),
            DashboardMetricResponse(
                label="Recent sales events",
                value=recent_sales_events,
                note="Recorded sale events currently stored in the event log.",
            ),
            DashboardMetricResponse(
                label="Pending A+ drafts",
                value=pending_aplus_drafts,
                note="Drafts not yet published to Amazon.",
            ),
        ]

        recent_activity = [
            ActivityItemResponse(
                title=row.event_type.replace("_", " ").title(),
                detail=f"{row.source} event is currently {row.status}.",
                occurred_at=row.occurred_at,
            )
            for row in recent_activity_rows
        ]
        inventory_alerts = [
            AlertItemResponse(
                title=f"Product alert for {row.product.sku}",
                detail=row.message,
                severity=row.severity,
                occurred_at=row.created_at,
            )
            for row in inventory_alert_rows
        ]
        slack_delivery = [
            SlackStatusItemResponse(
                notification_type=row.notification_type,
                status=row.status,
                message_preview=row.message_preview,
                created_at=row.created_at,
            )
            for row in slack_rows
        ]

        if not recent_activity:
            recent_activity = [
                ActivityItemResponse(
                    title="System ready",
                    detail="Auth, database, and dashboard APIs are available.",
                    occurred_at=self._now(),
                )
            ]

        if not inventory_alerts:
            inventory_alerts = [
                AlertItemResponse(
                    title="No active inventory alerts",
                    detail="Threshold-based inventory alerts will appear here once sync runs.",
                    severity=JobStatus.SUCCEEDED.value,
                    occurred_at=self._now(),
                )
            ]

        if not slack_delivery:
            slack_delivery = [
                SlackStatusItemResponse(
                    notification_type="slack",
                    status=JobStatus.PENDING.value,
                    message_preview="Slack delivery history will appear after notifications are sent.",
                    created_at=self._now(),
                )
            ]

        return DashboardSummaryResponse(
            metrics=metrics,
            recent_activity=recent_activity,
            inventory_alerts=inventory_alerts,
            slack_delivery=slack_delivery,
        )

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)
