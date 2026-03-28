from __future__ import annotations

from typing import Any

import httpx

from app.core.config import Settings, settings


class SlackWebhookService:
    def __init__(self, app_settings: Settings = settings) -> None:
        self.settings = app_settings

    def send_message(
        self,
        *,
        text: str,
        blocks: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if not self.settings.slack_webhook_url:
            raise ValueError("SLACK_WEBHOOK_URL is not configured.")

        payload: dict[str, Any] = {"text": text}
        if blocks:
            payload["blocks"] = blocks

        with httpx.Client(timeout=20) as client:
            response = client.post(
                self.settings.slack_webhook_url,
                headers={"Content-Type": "application/json"},
                json=payload,
            )
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise ValueError(
                    "Slack webhook request failed: "
                    f"{response.status_code} {response.text}"
                ) from exc

        return {
            "ok": True,
            "status_code": response.status_code,
            "body": response.text.strip() or "ok",
        }
