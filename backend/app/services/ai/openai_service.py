from __future__ import annotations

from decimal import Decimal
from typing import Any

import httpx

from app.core.config import Settings, settings
from app.schemas.aplus import AplusDraftPayload
from app.services.ai.prompt_templates import APLUS_SYSTEM_PROMPT, build_aplus_user_prompt


class OpenAiAplusService:
    def __init__(self, app_settings: Settings = settings) -> None:
        self.settings = app_settings

    def generate_aplus_draft(
        self,
        *,
        product_context: dict[str, Any],
        brand_tone: str | None,
        positioning: str | None,
    ) -> AplusDraftPayload:
        if not self.settings.openai_api_key:
            return self._mock_draft(
                product_context=product_context,
                brand_tone=brand_tone,
                positioning=positioning,
            )

        payload = {
            "model": self.settings.openai_model,
            "temperature": 0.4,
            "messages": [
                {"role": "system", "content": APLUS_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": build_aplus_user_prompt(
                        product_summary=self._format_product_summary(product_context),
                        brand_tone=brand_tone,
                        positioning=positioning,
                    ),
                },
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "amazon_aplus_draft",
                    "strict": True,
                    "schema": AplusDraftPayload.model_json_schema(),
                },
            },
        }

        with httpx.Client(timeout=90) as client:
            response = client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise ValueError(
                    "OpenAI request failed: "
                    f"{response.status_code} {response.text}"
                ) from exc

        body = response.json()
        message = body["choices"][0]["message"]
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("OpenAI did not return structured A+ draft content.")

        return AplusDraftPayload.model_validate_json(content)

    @staticmethod
    def _format_product_summary(product_context: dict[str, Any]) -> str:
        lines = []
        for key in ["title", "brand", "sku", "asin", "marketplace_id"]:
            value = product_context.get(key)
            if value:
                lines.append(f"{key}: {value}")

        price_amount = product_context.get("price_amount")
        price_currency = product_context.get("price_currency")
        if price_amount and price_currency:
            lines.append(f"price: {price_currency} {price_amount}")

        inventory = product_context.get("inventory")
        if isinstance(inventory, dict):
            lines.append(
                "inventory: "
                f"available={inventory.get('available_quantity', 0)}, "
                f"reserved={inventory.get('reserved_quantity', 0)}, "
                f"inbound={inventory.get('inbound_quantity', 0)}"
            )

        return "\n".join(lines)

    @staticmethod
    def _mock_draft(
        *,
        product_context: dict[str, Any],
        brand_tone: str | None,
        positioning: str | None,
    ) -> AplusDraftPayload:
        title = str(product_context.get("title") or "Amazon product")
        brand = str(product_context.get("brand") or "Brand")
        sku = str(product_context.get("sku") or "SKU")
        price_amount = product_context.get("price_amount")
        price_currency = product_context.get("price_currency") or "EUR"
        price_label = (
            f"{price_currency} {Decimal(str(price_amount))}"
            if price_amount is not None
            else "the listed marketplace price"
        )
        tone = brand_tone or "balanced and product-led"
        position = positioning or "practical everyday use"

        return AplusDraftPayload(
            headline=f"{brand} presentation for {title}",
            subheadline=f"Structured A+ storytelling for {sku} with a {tone} tone.",
            brand_story=(
                f"{brand} positions {title} around {position}, focusing on concrete product details "
                f"that support confident purchase decisions at {price_label}."
            ),
            key_features=[
                f"Marketplace-ready copy for {sku}",
                "Grounded product messaging without exaggerated claims",
                "Module structure prepared for editorial review",
            ],
            modules=[
                {
                    "module_type": "hero",
                    "headline": f"{title} at a glance",
                    "body": (
                        f"Open with a concise overview of {title}, explaining what the product is and "
                        "why the shopper should keep reading."
                    ),
                    "bullets": [
                        "Lead with the core purchase reason",
                        "Keep the message factual and skimmable",
                    ],
                    "image_brief": f"Hero image showing {title} in a clean ecommerce setting.",
                },
                {
                    "module_type": "feature",
                    "headline": "Product highlights",
                    "body": (
                        "Explain the most important product features using short, benefit-led paragraphs "
                        "that stay close to the supplied listing data."
                    ),
                    "bullets": [
                        "Focus on material, fit, or functional details",
                        "Avoid unsupported comparisons",
                        "Keep terminology marketplace safe",
                    ],
                    "image_brief": "Close-up detail shot that supports the main product features.",
                },
                {
                    "module_type": "comparison",
                    "headline": "Selection guidance",
                    "body": (
                        "Help customers understand which usage scenario or product variant fits them best "
                        "without making unverifiable superiority claims."
                    ),
                    "bullets": [
                        "Reference practical buying considerations",
                        "Call out sizing, color, or usage context",
                    ],
                    "image_brief": "Lifestyle or comparison visual showing product context.",
                },
            ],
            compliance_notes=[
                "Verify all feature statements against the live listing attributes before publishing.",
                "Replace image briefs with approved asset references during final editorial review.",
            ],
        )
