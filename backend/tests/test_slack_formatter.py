from datetime import datetime, timezone

from app.services.slack_formatter import SlackNotificationFormatter


FORMATTER = SlackNotificationFormatter()
NOW = datetime(2026, 3, 30, 10, 15, tzinfo=timezone.utc)


def test_formats_aplus_publish_with_structured_blocks() -> None:
    message = FORMATTER.format_message(
        event_type="aplus_publish",
        source="aplus_studio",
        event_status="in_review",
        payload={
            "marketplace_id": "A1PA6795UKMFR9",
            "sku": "DF-LPER-Z2CC",
            "asin": "B0GS3SHBNH",
            "draft_id": "draft-1234567890",
            "publish_status": "in_review",
            "content_reference_key": "REF-123",
        },
        occurred_at=NOW,
        notification_type="aplus_publish_success",
        message_preview="A+ content submitted to Amazon for DF-LPER-Z2CC.",
    )

    assert message.text.startswith("A+ content for DF-LPER-Z2CC")
    assert message.blocks[0]["text"]["text"] == "📦 A+ content submitted for review"
    assert any("*Marketplace*\nA1PA6795UKMFR9" == field["text"] for field in message.blocks[2]["fields"])
    assert any("*Reference*\nREF-123" == field["text"] for field in message.blocks[2]["fields"])


def test_formats_aplus_rejected_with_reason_emphasis() -> None:
    message = FORMATTER.format_message(
        event_type="aplus_publish",
        source="amazon_review_status",
        event_status="rejected",
        payload={
            "marketplace_id": "A1PA6795UKMFR9",
            "sku": "DF-LPER-Z2CC",
            "asin": "B0GS3SHBNH",
            "publish_status": "rejected",
            "content_reference_key": "REF-987",
            "rejection_reason": "Hero image crop is invalid for the supported module type.",
        },
        occurred_at=NOW,
        notification_type="aplus_rejected",
        message_preview="A+ content rejected for DF-LPER-Z2CC.",
    )

    assert message.blocks[0]["text"]["text"] == "❌ A+ content rejected"
    assert message.blocks[3]["text"]["text"].startswith("*Details*\nHero image crop is invalid")


def test_formats_new_order_as_compact_operational_card() -> None:
    message = FORMATTER.format_message(
        event_type="new_order",
        source="orders_api",
        event_status="new",
        payload={
            "marketplace_id": "A1PA6795UKMFR9",
            "order_id": "123-1234567-1234567",
            "sku": "DF-LPER-Z2CC",
            "asin": "B0GS3SHBNH",
            "quantity": 2,
            "status": "new",
            "product_title": "Seat Cover Set",
        },
        occurred_at=NOW,
        notification_type="new_order",
        message_preview="New Amazon order detected for DF-LPER-Z2CC.",
    )

    assert message.blocks[0]["text"]["text"] == "🛒 New Amazon order"
    assert any("*Quantity*\n2" == field["text"] for field in message.blocks[2]["fields"])
    assert "Seat Cover Set" in message.blocks[-1]["elements"][0]["text"]


def test_formats_low_stock_with_emphasis_section() -> None:
    message = FORMATTER.format_message(
        event_type="inventory_alert",
        source="inventory_sync",
        event_status="warning",
        payload={
            "marketplace_id": "A1PA6795UKMFR9",
            "sku": "DF-LPER-Z2CC",
            "asin": "B0GS3SHBNH",
            "available_quantity": 3,
            "threshold": 5,
            "stock_health": "low_stock",
            "message": "Available stock is below the configured threshold.",
        },
        occurred_at=NOW,
        notification_type="low_stock_threshold_reached",
        message_preview="Low stock alert for DF-LPER-Z2CC.",
    )

    assert message.blocks[0]["text"]["text"] == "⚠️ Low stock alert"
    assert any("*Health*\nLow Stock" == field["text"] for field in message.blocks[2]["fields"])
    assert message.blocks[3]["text"]["text"] == "*Details*\nAvailable stock is below the configured threshold."
