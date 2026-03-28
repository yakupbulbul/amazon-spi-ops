from __future__ import annotations

from decimal import Decimal
import json
from typing import Any

import httpx

from app.core.config import Settings, settings
from app.schemas.aplus import AplusDraftPayload
from app.services.ai.prompt_templates import (
    APLUS_SYSTEM_PROMPT,
    build_aplus_translation_prompt,
    build_aplus_user_prompt,
    get_language_market_guidance,
)


class OpenAiAplusService:
    def __init__(self, app_settings: Settings = settings) -> None:
        self.settings = app_settings

    def generate_aplus_draft(
        self,
        *,
        product_context: dict[str, Any],
        brand_tone: str | None,
        positioning: str | None,
        source_language: str,
    ) -> AplusDraftPayload:
        if not self.settings.openai_api_key:
            return self._mock_draft(
                product_context=product_context,
                brand_tone=brand_tone,
                positioning=positioning,
                source_language=source_language,
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
                        language=source_language,
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

    def translate_aplus_draft(
        self,
        *,
        draft_payload: AplusDraftPayload,
        source_language: str,
        target_language: str,
    ) -> AplusDraftPayload:
        if source_language == target_language:
            raise ValueError("Source and target language must be different when translation is enabled.")

        if not self.settings.openai_api_key:
            return self._mock_translate_draft(draft_payload=draft_payload, target_language=target_language)

        payload = {
            "model": self.settings.openai_model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": APLUS_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": build_aplus_translation_prompt(
                        source_language=source_language,
                        target_language=target_language,
                        draft_payload=draft_payload.model_dump_json(indent=2),
                    ),
                },
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "amazon_aplus_translation",
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
                    "OpenAI translation request failed: "
                    f"{response.status_code} {response.text}"
                ) from exc

        body = response.json()
        message = body["choices"][0]["message"]
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("OpenAI did not return translated A+ draft content.")

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
        source_language: str,
    ) -> AplusDraftPayload:
        title = str(product_context.get("title") or "Amazon product")
        brand = str(product_context.get("brand") or "Brand")
        price_amount = product_context.get("price_amount")
        price_currency = product_context.get("price_currency") or "EUR"
        price_label = (
            f"{price_currency} {Decimal(str(price_amount))}"
            if price_amount is not None
            else "the listed marketplace price"
        )
        tone = brand_tone or "balanced and product-led"
        position = positioning or "practical everyday use for detail-focused shoppers"
        locale_guidance = get_language_market_guidance(source_language)

        hero_headline, hero_subheadline = OpenAiAplusService._mock_headline_pack(
            title=title,
            source_language=source_language,
        )
        key_benefits = OpenAiAplusService._mock_key_benefits(
            source_language=source_language,
            position=position,
        )
        hero_body = OpenAiAplusService._mock_hero_body(
            title=title,
            brand=brand,
            position=position,
            tone=tone,
            locale_guidance=locale_guidance,
        )

        return AplusDraftPayload(
            headline=hero_headline,
            subheadline=hero_subheadline,
            brand_story=(
                f"{brand} positions {title} for {position}, combining {tone} messaging with concrete reasons "
                f"to choose it over generic alternatives. The story should reassure shoppers about fit, usability, "
                f"and lasting value at {price_label} while staying aligned with {locale_guidance.lower()}"
            ),
            key_features=key_benefits,
            modules=[
                {
                    "module_type": "hero",
                    "headline": hero_headline,
                    "body": hero_body,
                    "bullets": [
                        OpenAiAplusService._localize_copy(
                            source_language,
                            de="Präziser Nutzen auf den ersten Blick",
                            en="Lead with the main shopper benefit",
                        ),
                        OpenAiAplusService._localize_copy(
                            source_language,
                            de="Warum das Produkt im Alltag überzeugt",
                            en="Explain why it matters in everyday use",
                        ),
                    ],
                    "image_brief": OpenAiAplusService._localize_copy(
                        source_language,
                        de=f"Zeige {title} in einer glaubwürdigen Alltagsszene; Overlay-Text: 'Für sichere Routine gemacht'.",
                        en=f"Show {title} in a real-life usage scene; overlay text: 'Built for confident daily use'.",
                    ),
                },
                {
                    "module_type": "feature",
                    "headline": OpenAiAplusService._localize_copy(
                        source_language,
                        de="Vorteile, die zählen",
                        en="Benefits that land",
                    ),
                    "body": OpenAiAplusService._localize_copy(
                        source_language,
                        de=(
                            f"Konzentriere dich auf die Merkmale, die für {position} den größten Unterschied machen. "
                            "Beschreibe nicht nur das Produktdetail, sondern den spürbaren Vorteil für Komfort, Sicherheit oder Alltagstempo."
                        ),
                        en=(
                            f"Focus on the details that make the biggest difference for {position}. "
                            "Every line should connect the product feature to a practical shopper outcome."
                        ),
                    ),
                    "bullets": [
                        key_benefits[0],
                        key_benefits[1],
                        key_benefits[2],
                    ],
                    "image_brief": OpenAiAplusService._localize_copy(
                        source_language,
                        de="Zeige Nahaufnahmen von Material, Verarbeitung oder Funktion; Overlay-Text: 'Mehr Komfort im Einsatz'.",
                        en="Show close-up detail photography of materials or function; overlay text: 'Comfort where it counts'.",
                    ),
                },
                {
                    "module_type": "feature",
                    "headline": OpenAiAplusService._localize_copy(
                        source_language,
                        de="Passt in den Alltag",
                        en="Fits real routines",
                    ),
                    "body": OpenAiAplusService._localize_copy(
                        source_language,
                        de=(
                            f"Zeige konkrete Einsatzmomente für {position}. Die Sprache soll Nutzungsbilder erzeugen und erklären, "
                            "warum das Produkt im Tagesablauf leichter, angenehmer oder verlässlicher wirkt."
                        ),
                        en=(
                            f"Show clear usage scenarios for {position}. Help the shopper picture where the product makes daily life easier, smoother, or more dependable."
                        ),
                    ),
                    "bullets": [
                        OpenAiAplusService._localize_copy(source_language, de="Für wiederkehrende Nutzung gedacht", en="Built for repeat use"),
                        OpenAiAplusService._localize_copy(source_language, de="Leicht in bestehende Routinen integrierbar", en="Easy to fit into existing routines"),
                        OpenAiAplusService._localize_copy(source_language, de="Unterstützt Komfort und Sicherheit im Alltag", en="Supports comfort and confidence day to day"),
                    ],
                    "image_brief": OpenAiAplusService._localize_copy(
                        source_language,
                        de="Lifestyle-Szene mit klar erkennbarem Anwendungsfall; Overlay-Text: 'Bereit für jeden Tag'.",
                        en="Lifestyle scene showing the product in use; overlay text: 'Ready for every day'.",
                    ),
                },
                {
                    "module_type": "comparison",
                    "headline": OpenAiAplusService._localize_copy(
                        source_language,
                        de="Mehr als Standard",
                        en="Beyond the generic option",
                    ),
                    "body": OpenAiAplusService._localize_copy(
                        source_language,
                        de=(
                            "Vergleiche das Produkt mit generischen Alternativen anhand klarer Kaufkriterien wie Komfort, Verlässlichkeit, Materialgefühl oder Alltagstauglichkeit."
                        ),
                        en=(
                            "Compare the product against generic alternatives using concrete buying criteria such as comfort, reliability, feel, and day-to-day usability."
                        ),
                    ),
                    "bullets": [
                        OpenAiAplusService._localize_copy(source_language, de="Gezielter Nutzen statt austauschbarer Standardlösung", en="Specific shopper benefit over generic basics"),
                        OpenAiAplusService._localize_copy(source_language, de="Bessere Alltagstauglichkeit ohne leere Superlative", en="Stronger everyday usability without empty hype"),
                        OpenAiAplusService._localize_copy(source_language, de="Klarere Kaufentscheidung durch konkrete Vorteile", en="Clearer purchase decision through concrete advantages"),
                    ],
                    "image_brief": OpenAiAplusService._localize_copy(
                        source_language,
                        de="Einfaches Vergleichsbild mit generischen Alternativen; Overlay-Text: 'Warum es sich lohnt'.",
                        en="Simple comparison visual against generic alternatives; overlay text: 'Why it stands out'.",
                    ),
                },
                {
                    "module_type": "faq",
                    "headline": OpenAiAplusService._localize_copy(
                        source_language,
                        de="Vertrauen bei jedem Schritt",
                        en="Confidence in every detail",
                    ),
                    "body": OpenAiAplusService._localize_copy(
                        source_language,
                        de=(
                            f"Schließe mit einer vertrauensbildenden Sektion ab, die Verarbeitung, Qualitätsanspruch und die Eignung für {position} betont. "
                            "Die Sprache soll Sicherheit geben und letzte Zweifel abbauen."
                        ),
                        en=(
                            f"Close with a reassurance section that reinforces craftsmanship, quality intent, and fit for {position}. "
                            "This section should reduce hesitation and increase trust."
                        ),
                    ),
                    "bullets": [
                        OpenAiAplusService._localize_copy(source_language, de="Kaufrelevante Qualität klar erklärt", en="Quality signals explained in buying terms"),
                        OpenAiAplusService._localize_copy(source_language, de="Vertrauenssignale ohne leere Behauptungen", en="Trust-building copy without vague claims"),
                    ],
                    "image_brief": OpenAiAplusService._localize_copy(
                        source_language,
                        de="Ruhige Qualitätsaufnahme oder Detail-Visual; Overlay-Text: 'Entwickelt für langfristige Zufriedenheit'.",
                        en="Calm quality-detail visual; overlay text: 'Designed for long-term confidence'.",
                    ),
                },
            ],
            compliance_notes=[
                OpenAiAplusService._localize_copy(
                    source_language,
                    de="Prüfe alle Nutzenaussagen gegen freigegebene Listing-Daten, bevor der Entwurf veröffentlicht wird.",
                    en="Verify every benefit statement against approved listing data before publishing.",
                ),
                OpenAiAplusService._localize_copy(
                    source_language,
                    de="Vergleiche dürfen sich nur auf generische Alternativen beziehen und keine benannten Wettbewerber enthalten.",
                    en="Comparison claims must reference generic alternatives only and must not name competitors.",
                ),
                OpenAiAplusService._localize_copy(
                    source_language,
                    de="Overlay-Texte und Bildideen vor dem finalen Creative-Briefing fachlich abstimmen.",
                    en="Confirm overlay copy and image direction with the final creative brief before launch.",
                ),
            ],
        )

    @staticmethod
    def _mock_translate_draft(
        *,
        draft_payload: AplusDraftPayload,
        target_language: str,
    ) -> AplusDraftPayload:
        payload = draft_payload.model_dump(mode="json")
        non_translatable_keys = {
            "module_type",
            "image_mode",
            "generated_image_url",
            "uploaded_image_url",
            "selected_asset_id",
            "reference_asset_ids",
            "image_status",
            "image_error_message",
        }

        def translate_text(value: Any) -> Any:
            if isinstance(value, str):
                return f"{value} ({target_language})"
            if isinstance(value, list):
                return [translate_text(item) for item in value]
            if isinstance(value, dict):
                translated: dict[str, Any] = {}
                for key, nested_value in value.items():
                    if key in non_translatable_keys:
                        translated[key] = nested_value
                    else:
                        translated[key] = translate_text(nested_value)
                return translated
            return value

        translated_payload = json.loads(json.dumps(payload))
        for key in ["headline", "subheadline", "brand_story", "key_features", "modules", "compliance_notes"]:
            translated_payload[key] = translate_text(translated_payload[key])

        return AplusDraftPayload.model_validate(translated_payload)

    @staticmethod
    def _mock_headline_pack(*, title: str, source_language: str) -> tuple[str, str]:
        if source_language == "de-DE":
            return (
                "Klarer Nutzen. Jeden Tag.",
                f"{title} verbindet präzise Vorteile mit sicherem Alltagskomfort.",
            )
        if source_language == "fr-FR":
            return (
                "Un bénéfice immédiat",
                f"{title} rend l'usage quotidien plus fluide, plus clair et plus rassurant.",
            )
        if source_language == "it-IT":
            return (
                "Valore che si sente",
                f"{title} unisce comfort quotidiano, chiarezza d'uso e stile funzionale.",
            )
        if source_language == "es-ES":
            return (
                "Ventajas que se notan",
                f"{title} aporta comodidad diaria y una elección más segura desde el primer uso.",
            )
        return (
            "Comfort with purpose",
            f"{title} is built to make everyday use feel easier, clearer, and more dependable.",
        )

    @staticmethod
    def _mock_key_benefits(*, source_language: str, position: str) -> list[str]:
        if source_language == "de-DE":
            return [
                "Mehr Sicherheit und Klarheit im täglichen Einsatz",
                f"Passt zu {position} statt nur technische Details zu nennen",
                "Spürbarer Komfortgewinn gegenüber generischen Alternativen",
                "Verlässliche Wirkung ohne übertriebene Werbeversprechen",
            ]
        return [
            "Turns product detail into a clear everyday benefit",
            f"Fits {position} with more relevance than generic alternatives",
            "Adds comfort and confidence where shoppers actually feel it",
            "Explains differentiation without vague quality language",
        ]

    @staticmethod
    def _mock_hero_body(
        *,
        title: str,
        brand: str,
        position: str,
        tone: str,
        locale_guidance: str,
    ) -> str:
        return (
            f"{brand} positions {title} for {position}, using a {tone} tone that stays shopper-focused and conversion-ready. "
            f"The opening section should make the value proposition obvious fast, explain the main purchase reason, and follow this guidance: {locale_guidance}"
        )

    @staticmethod
    def _localize_copy(source_language: str, *, de: str, en: str) -> str:
        return de if source_language == "de-DE" else en
