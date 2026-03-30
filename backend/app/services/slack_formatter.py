from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class SlackMessage:
    text: str
    blocks: list[dict[str, Any]]


class SlackNotificationFormatter:
    def format_message(
        self,
        *,
        event_type: str,
        source: str,
        event_status: str,
        payload: dict[str, object],
        occurred_at: datetime,
        notification_type: str,
        message_preview: str,
    ) -> SlackMessage:
        formatter = {
            "aplus_publish_success": self._format_aplus_publish,
            "aplus_publish_failure": self._format_aplus_rejected,
            "aplus_approved": self._format_aplus_approved,
            "aplus_rejected": self._format_aplus_rejected,
            "low_stock_threshold_reached": self._format_low_stock,
            "price_update_success": self._format_price_update,
            "price_update_failure": self._format_price_update,
            "stock_update_success": self._format_stock_update,
            "stock_update_failure": self._format_stock_update,
            "slack_test": self._format_slack_test,
            "new_order": self._format_new_order,
            "system_error": self._format_system_error,
        }.get(notification_type, self._format_generic)
        return formatter(
            source=source,
            event_type=event_type,
            event_status=event_status,
            payload=payload,
            occurred_at=occurred_at,
            notification_type=notification_type,
            message_preview=message_preview,
        )

    def _format_aplus_publish(self, **kwargs: Any) -> SlackMessage:
        payload = kwargs["payload"]
        status = str(payload.get("publish_status") or kwargs["event_status"] or "submitted")
        emoji = "📦" if status in {"submitted", "in_review", "assets_prepared", "validated"} else "📝"
        sku = self._string(payload, "sku")
        title = f"{emoji} A+ content submitted for review"
        summary = f"A+ content for {sku or 'the selected SKU'} has been submitted to Amazon and is now in review."
        fields = [
            self._field("Status", self._humanize(status)),
            self._field("Marketplace", self._string(payload, "marketplace_id")),
            self._field("SKU", sku),
            self._field("ASIN", self._string(payload, "asin")),
            self._field("Draft", self._short_id(self._string(payload, "draft_id"))),
            self._field("Reference", self._string(payload, "content_reference_key")),
        ]
        return self._build_message(
            title=title,
            summary=summary,
            fields=fields,
            source=kwargs["source"],
            occurred_at=kwargs["occurred_at"],
            fallback=summary,
        )

    def _format_aplus_approved(self, **kwargs: Any) -> SlackMessage:
        payload = kwargs["payload"]
        sku = self._string(payload, "sku")
        summary = f"A+ content for {sku or 'the selected SKU'} has been approved by Amazon."
        fields = [
            self._field("Marketplace", self._string(payload, "marketplace_id")),
            self._field("SKU", sku),
            self._field("ASIN", self._string(payload, "asin")),
            self._field("Status", "Approved"),
            self._field("Reference", self._string(payload, "content_reference_key")),
        ]
        return self._build_message(
            title="✅ A+ content approved",
            summary=summary,
            fields=fields,
            source=kwargs["source"],
            occurred_at=kwargs["occurred_at"],
            fallback=summary,
        )

    def _format_aplus_rejected(self, **kwargs: Any) -> SlackMessage:
        payload = kwargs["payload"]
        sku = self._string(payload, "sku")
        reason = (
            self._string(payload, "rejection_reason")
            or self._string(payload, "error")
            or "Amazon returned a rejection without a detailed reason."
        )
        summary = f"A+ content for {sku or 'the selected SKU'} was rejected by Amazon."
        fields = [
            self._field("Marketplace", self._string(payload, "marketplace_id")),
            self._field("SKU", sku),
            self._field("ASIN", self._string(payload, "asin")),
            self._field("Status", self._humanize(self._string(payload, "publish_status") or kwargs["event_status"])),
            self._field("Reference", self._string(payload, "content_reference_key")),
        ]
        return self._build_message(
            title="❌ A+ content rejected",
            summary=summary,
            fields=fields,
            source=kwargs["source"],
            occurred_at=kwargs["occurred_at"],
            fallback=f"{summary} Reason: {reason}",
            emphasis=reason,
        )

    def _format_new_order(self, **kwargs: Any) -> SlackMessage:
        payload = kwargs["payload"]
        summary = "A new order was detected for your Amazon store."
        fields = [
            self._field("Marketplace", self._string(payload, "marketplace_id")),
            self._field("Order", self._short_id(self._string(payload, "order_id"), keep=14)),
            self._field("Status", self._humanize(self._string(payload, "status") or kwargs["event_status"])),
            self._field("SKU", self._string(payload, "sku")),
            self._field("ASIN", self._string(payload, "asin")),
            self._field("Quantity", self._string(payload, "quantity")),
        ]
        context = self._string(payload, "product_title")
        return self._build_message(
            title="🛒 New Amazon order",
            summary=summary,
            fields=fields,
            source=kwargs["source"],
            occurred_at=kwargs["occurred_at"],
            fallback=summary,
            context_note=context,
        )

    def _format_low_stock(self, **kwargs: Any) -> SlackMessage:
        payload = kwargs["payload"]
        available = self._string(payload, "available_quantity")
        threshold = self._string(payload, "threshold")
        summary = f"{self._string(payload, 'sku') or 'This SKU'} is at or below the configured stock threshold."
        fields = [
            self._field("Marketplace", self._string(payload, "marketplace_id")),
            self._field("SKU", self._string(payload, "sku")),
            self._field("ASIN", self._string(payload, "asin")),
            self._field("Available", available),
            self._field("Threshold", threshold),
            self._field("Health", self._humanize(self._string(payload, "stock_health") or kwargs["event_status"])),
        ]
        emphasis = self._string(payload, "message") or f"Available stock: {available} / threshold: {threshold}"
        return self._build_message(
            title="⚠️ Low stock alert",
            summary=summary,
            fields=fields,
            source=kwargs["source"],
            occurred_at=kwargs["occurred_at"],
            fallback=f"{summary} {emphasis}",
            emphasis=emphasis,
        )

    def _format_price_update(self, **kwargs: Any) -> SlackMessage:
        payload = kwargs["payload"]
        success = kwargs["notification_type"].endswith("success")
        title = "💶 Price updated" if success else "❌ Price update failed"
        currency = self._string(payload, "currency")
        new_value = self._string(payload, "new_price_amount") or self._string(payload, "attempted_price_amount")
        summary = (
            f"{self._string(payload, 'sku') or 'The selected SKU'} price was "
            f"{'updated' if success else 'submitted for update'} to {currency} {new_value}."
        ).strip()
        fields = [
            self._field("Marketplace", self._string(payload, "marketplace_id")),
            self._field("SKU", self._string(payload, "sku")),
            self._field("ASIN", self._string(payload, "asin")),
            self._field("Old price", self._format_money(payload.get("old_price_amount"), currency)),
            self._field("New price", self._format_money(new_value, currency)),
            self._field("Result", "Succeeded" if success else "Failed"),
        ]
        return self._build_message(
            title=title,
            summary=summary,
            fields=fields,
            source=kwargs["source"],
            occurred_at=kwargs["occurred_at"],
            fallback=summary,
            emphasis=self._string(payload, "error") if not success else None,
        )

    def _format_stock_update(self, **kwargs: Any) -> SlackMessage:
        payload = kwargs["payload"]
        success = kwargs["notification_type"].endswith("success")
        title = "📦 Stock updated" if success else "❌ Stock update failed"
        new_quantity = self._string(payload, "new_quantity") or self._string(payload, "attempted_quantity")
        summary = (
            f"{self._string(payload, 'sku') or 'The selected SKU'} stock was "
            f"{'updated' if success else 'submitted for update'} to {new_quantity}."
        ).strip()
        fields = [
            self._field("Marketplace", self._string(payload, "marketplace_id")),
            self._field("SKU", self._string(payload, "sku")),
            self._field("ASIN", self._string(payload, "asin")),
            self._field("Old quantity", self._string(payload, "old_quantity")),
            self._field("New quantity", new_quantity),
            self._field("Result", "Succeeded" if success else "Failed"),
        ]
        return self._build_message(
            title=title,
            summary=summary,
            fields=fields,
            source=kwargs["source"],
            occurred_at=kwargs["occurred_at"],
            fallback=summary,
            emphasis=self._string(payload, "error") if not success else None,
        )

    def _format_slack_test(self, **kwargs: Any) -> SlackMessage:
        payload = kwargs["payload"]
        summary = "Slack delivery is configured and the notification pipeline completed successfully."
        fields = [
            self._field("Requested by", self._string(payload, "requested_by")),
            self._field("Source", kwargs["source"]),
            self._field("Status", "Succeeded"),
        ]
        return self._build_message(
            title="✅ Slack notification test",
            summary=summary,
            fields=fields,
            source=kwargs["source"],
            occurred_at=kwargs["occurred_at"],
            fallback=summary,
        )

    def _format_system_error(self, **kwargs: Any) -> SlackMessage:
        payload = kwargs["payload"]
        summary = self._string(payload, "summary") or "A system error requires attention."
        fields = [
            self._field("Service", self._string(payload, "service")),
            self._field("Status", self._humanize(kwargs["event_status"])),
            self._field("Source", kwargs["source"]),
        ]
        return self._build_message(
            title="🚨 System error",
            summary=summary,
            fields=fields,
            source=kwargs["source"],
            occurred_at=kwargs["occurred_at"],
            fallback=summary,
            emphasis=self._string(payload, "error"),
        )

    def _format_generic(self, **kwargs: Any) -> SlackMessage:
        summary = kwargs["message_preview"]
        fields = [
            self._field("Event", self._humanize(kwargs["event_type"])),
            self._field("Status", self._humanize(kwargs["event_status"])),
            self._field("Source", kwargs["source"]),
        ]
        return self._build_message(
            title="🔔 Operational update",
            summary=summary,
            fields=fields,
            source=kwargs["source"],
            occurred_at=kwargs["occurred_at"],
            fallback=summary,
        )

    def _build_message(
        self,
        *,
        title: str,
        summary: str,
        fields: list[dict[str, str]],
        source: str,
        occurred_at: datetime,
        fallback: str,
        emphasis: str | None = None,
        context_note: str | None = None,
    ) -> SlackMessage:
        blocks: list[dict[str, Any]] = [
            {"type": "header", "text": {"type": "plain_text", "text": title[:150]}},
            {"type": "section", "text": {"type": "mrkdwn", "text": summary[:3000]}},
        ]
        usable_fields = [field for field in fields if field["value"]]
        if usable_fields:
            blocks.append(
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f'*{field["label"]}*\n{field["value"][:200]}'}
                        for field in usable_fields[:10]
                    ],
                }
            )
        if emphasis:
            blocks.append(
                {"type": "section", "text": {"type": "mrkdwn", "text": f'*Details*\n{emphasis[:2800]}'}}
            )
        context_parts = [
            f"Source: {source}",
            f"Time: {occurred_at.strftime('%Y-%m-%d %H:%M UTC')}",
        ]
        if context_note:
            context_parts.append(context_note)
        blocks.append(
            {"type": "context", "elements": [{"type": "mrkdwn", "text": ' • '.join(context_parts)[:3000]}]}
        )
        return SlackMessage(text=fallback[:3000], blocks=blocks)

    @staticmethod
    def _field(label: str, value: object | None) -> dict[str, str]:
        return {"label": label, "value": "" if value is None else str(value)}

    @staticmethod
    def _short_id(value: str | None, *, keep: int = 10) -> str:
        if not value:
            return ""
        if len(value) <= keep:
            return value
        return f"{value[:keep]}…"

    @staticmethod
    def _humanize(value: str | None) -> str:
        if not value:
            return ""
        return value.replace("_", " ").replace("-", " ").title()

    @staticmethod
    def _string(payload: dict[str, object], key: str) -> str:
        value = payload.get(key)
        if value is None:
            return ""
        return str(value)

    @staticmethod
    def _format_money(amount: object | None, currency: str | None) -> str:
        if amount in (None, ""):
            return ""
        if currency:
            return f"{currency} {amount}"
        return str(amount)
