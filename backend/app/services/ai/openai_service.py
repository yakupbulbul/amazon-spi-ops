from __future__ import annotations

from decimal import Decimal
import json
from typing import Any

import httpx
from pydantic import BaseModel

from app.core.config import Settings, settings
from app.schemas.aplus import (
    AplusDraftImprovementPatch,
    AplusDraftPayload,
    SupportedAplusImprovementCategory,
)
from app.services.ai.prompt_templates import (
    APLUS_SYSTEM_PROMPT,
    build_aplus_improvement_prompt,
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
                    "schema": self._openai_response_schema(AplusDraftPayload),
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
                    "schema": self._openai_response_schema(AplusDraftPayload),
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

        try:
            translated_payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError("OpenAI returned invalid JSON for translated A+ draft content.") from exc

        return self._merge_translated_payload(
            original_payload=draft_payload,
            translated_payload=translated_payload,
        )

    def improve_aplus_draft(
        self,
        *,
        draft_payload: AplusDraftPayload,
        category: SupportedAplusImprovementCategory,
        issues: list[str],
        language: str,
        product_context: dict[str, Any],
    ) -> tuple[AplusDraftPayload, str]:
        if not self.settings.openai_api_key:
            patch = self._mock_improvement_patch(
                draft_payload=draft_payload,
                category=category,
                issues=issues,
                language=language,
            )
            improved_payload = self._apply_improvement_patch(
                original_payload=draft_payload,
                improvement_patch=patch,
            )
            return improved_payload, patch.summary

        payload = {
            "model": self.settings.openai_model,
            "temperature": 0.3,
            "messages": [
                {"role": "system", "content": APLUS_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": build_aplus_improvement_prompt(
                        category=category,
                        language=language,
                        product_summary=self._format_product_summary(product_context),
                        issues=issues,
                        draft_payload=draft_payload.model_dump_json(indent=2),
                    ),
                },
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "amazon_aplus_improvement_patch",
                    "strict": True,
                    "schema": self._openai_response_schema(AplusDraftImprovementPatch),
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
                    "OpenAI improvement request failed: "
                    f"{response.status_code} {response.text}"
                ) from exc

        body = response.json()
        message = body["choices"][0]["message"]
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("OpenAI did not return structured A+ improvement content.")

        patch = AplusDraftImprovementPatch.model_validate_json(content)
        improved_payload = self._apply_improvement_patch(
            original_payload=draft_payload,
            improvement_patch=patch,
        )
        return improved_payload, patch.summary

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
    def _openai_response_schema(schema_model: type[BaseModel] = AplusDraftPayload) -> dict[str, Any]:
        schema = schema_model.model_json_schema()
        OpenAiAplusService._require_all_object_properties(schema)
        return schema

    @staticmethod
    def _require_all_object_properties(node: Any) -> None:
        if isinstance(node, dict):
            properties = node.get("properties")
            if isinstance(properties, dict) and properties:
                node["required"] = list(properties.keys())

            for value in node.values():
                OpenAiAplusService._require_all_object_properties(value)
            return

        if isinstance(node, list):
            for item in node:
                OpenAiAplusService._require_all_object_properties(item)

    @staticmethod
    def _mock_improvement_patch(
        *,
        draft_payload: AplusDraftPayload,
        category: SupportedAplusImprovementCategory,
        issues: list[str],
        language: str,
    ) -> AplusDraftImprovementPatch:
        summary = {
            "structure": "Reframed the hero and supporting modules so the draft reads with clearer section roles.",
            "clarity": "Shortened dense copy and made the benefits easier to scan quickly.",
            "differentiation": "Replaced generic quality language with clearer product advantages over generic alternatives.",
            "completeness": "Added practical context and clearer buying details without rewriting unrelated sections.",
        }[category]
        issue_hint = issues[0] if issues else ""
        hero_module = next((module for module in draft_payload.modules if module.module_type == "hero"), None)
        feature_modules = [module for module in draft_payload.modules if module.module_type == "feature"]

        if language == "de-DE":
            if category == "differentiation":
                return AplusDraftImprovementPatch(
                    summary=summary,
                    subheadline="Konkreter Nutzen statt allgemeiner Qualitätsversprechen.",
                    brand_story=f"{draft_payload.brand_story} Der Fokus liegt jetzt stärker auf dem spürbaren Unterschied gegenüber generischen Alternativen und darauf, warum dieser Vorteil im Alltag zählt.".strip(),
                    key_features=[
                        feature.replace("hochwertig", "so verarbeitet, dass Passform, Komfort oder Alltagseinsatz klarer profitieren")
                        for feature in draft_payload.key_features
                    ],
                    modules=[
                        {
                            "module_id": hero_module.module_id if hero_module else draft_payload.modules[0].module_id,
                            "headline": "Warum es im Alltag zählt",
                            "body": f"{hero_module.body if hero_module else draft_payload.modules[0].body} Erkläre den konkreten Vorteil gegenüber generischen Alternativen statt nur Qualität zu behaupten.".strip(),
                            "bullets": None,
                        },
                        *[
                            {
                                "module_id": module.module_id,
                                "headline": module.headline.replace("Vorteile", "Konkrete Vorteile"),
                                "body": f"{module.body} Benenne klar, welcher Nutzen entsteht und warum die Lösung präziser wirkt als eine generische Alternative.".strip(),
                                "bullets": [
                                    bullet.replace("hochwertig", "gezielt für den spürbaren Alltagsnutzen entwickelt")
                                    for bullet in module.bullets
                                ],
                            }
                            for module in feature_modules[:2]
                        ],
                    ],
                )
            if category == "clarity":
                return AplusDraftImprovementPatch(
                    summary=summary,
                    headline="Klarer Nutzen auf einen Blick",
                    subheadline=draft_payload.subheadline[:120].rstrip(". ") + ".",
                    modules=[
                        {
                            "module_id": module.module_id,
                            "headline": module.headline[:64].rstrip(". "),
                            "body": " ".join(module.body.split(". ")[:2]).strip(),
                            "bullets": module.bullets[:3],
                        }
                        for module in draft_payload.modules[:3]
                    ],
                )
            if category == "structure":
                return AplusDraftImprovementPatch(
                    summary=summary,
                    brand_story=f"{draft_payload.brand_story} {issue_hint}".strip(),
                    modules=[
                        {
                            "module_id": draft_payload.modules[0].module_id,
                            "headline": "Der Hauptnutzen zuerst",
                            "body": f"{draft_payload.modules[0].body} Diese Sektion soll den Hauptkaufgrund zuerst verankern.".strip(),
                            "bullets": draft_payload.modules[0].bullets,
                        },
                        *[
                            {
                                "module_id": module.module_id,
                                "headline": module.headline,
                                "body": f"{module.body} Diese Sektion unterstützt den Hero mit einem klar abgegrenzten Folgeargument.".strip(),
                                "bullets": module.bullets,
                            }
                            for module in draft_payload.modules[1:3]
                        ],
                    ],
                )
            return AplusDraftImprovementPatch(
                summary=summary,
                brand_story=f"{draft_payload.brand_story} Ergänze Material-, Nutzungs- oder Einsatzdetails, damit offene Käuferfragen früher beantwortet werden.".strip(),
                key_features=[
                    *draft_payload.key_features[:2],
                    "Erklärt genauer, wann, wie und für wen der Vorteil im Alltag spürbar wird",
                    *draft_payload.key_features[2:],
                ][:6],
                modules=[
                    {
                        "module_id": module.module_id,
                        "headline": module.headline,
                        "body": f"{module.body} Füge eine konkrete Nutzungs- oder Materialerklärung hinzu, damit der Kaufkontext klarer wird.".strip(),
                        "bullets": module.bullets,
                    }
                    for module in draft_payload.modules[:2]
                ],
            )

        if category == "differentiation":
            return AplusDraftImprovementPatch(
                summary=summary,
                subheadline="Sharper reasons to choose this over generic alternatives.",
                brand_story=f"{draft_payload.brand_story} This version leans harder into the practical advantage the shopper gets versus a generic option.".strip(),
                key_features=[
                    feature.replace("high quality", "built to deliver a clearer everyday advantage")
                    .replace("premium quality", "built to solve a more specific everyday need")
                    for feature in draft_payload.key_features
                ],
                modules=[
                    {
                        "module_id": module.module_id,
                        "headline": "A more specific advantage" if index == 0 else module.headline,
                        "body": f"{module.body} Make the distinction versus a generic alternative explicit and shopper-relevant.".strip(),
                        "bullets": [
                            bullet.replace("high quality", "designed to create a more useful everyday result")
                            .replace("premium quality", "designed around a clearer practical benefit")
                            for bullet in module.bullets
                        ],
                    }
                    for index, module in enumerate(draft_payload.modules[:3])
                ],
            )

        if category == "clarity":
            return AplusDraftImprovementPatch(
                summary=summary,
                headline="Clear value, faster",
                subheadline=draft_payload.subheadline[:120].rstrip(". ") + ".",
                modules=[
                    {
                        "module_id": module.module_id,
                        "headline": module.headline[:64].rstrip(". "),
                        "body": " ".join(module.body.split(". ")[:2]).strip(),
                        "bullets": module.bullets[:3],
                    }
                    for module in draft_payload.modules[:3]
                ],
            )

        if category == "structure":
            return AplusDraftImprovementPatch(
                summary=summary,
                brand_story=f"{draft_payload.brand_story} Each section now reinforces a clearer editorial role in the overall A+ story.".strip(),
                modules=[
                    {
                        "module_id": draft_payload.modules[0].module_id,
                        "headline": "Lead with the main benefit",
                        "body": f"{draft_payload.modules[0].body} This opening section now anchors the primary purchase reason first.".strip(),
                        "bullets": draft_payload.modules[0].bullets,
                    },
                    *[
                        {
                            "module_id": module.module_id,
                            "headline": module.headline,
                            "body": f"{module.body} This module now supports the draft with a more distinct follow-on role.".strip(),
                            "bullets": module.bullets,
                        }
                        for module in draft_payload.modules[1:3]
                    ],
                ],
            )

        return AplusDraftImprovementPatch(
            summary=summary,
            brand_story=f"{draft_payload.brand_story} Add more practical product detail so the shopper understands fit, use, and decision context earlier.".strip(),
            key_features=[
                *draft_payload.key_features[:2],
                "Explains a practical usage detail the shopper would otherwise have to infer",
                *draft_payload.key_features[2:],
            ][:6],
            modules=[
                {
                    "module_id": module.module_id,
                    "headline": module.headline,
                    "body": f"{module.body} Add one practical detail about use, fit, or care so the section answers a real shopper question.".strip(),
                    "bullets": module.bullets,
                }
                for module in draft_payload.modules[:2]
            ],
        )

    @staticmethod
    def _apply_improvement_patch(
        *,
        original_payload: AplusDraftPayload,
        improvement_patch: AplusDraftImprovementPatch,
    ) -> AplusDraftPayload:
        merged_payload = original_payload.model_dump(mode="json")

        for field in ["headline", "subheadline", "brand_story"]:
            value = getattr(improvement_patch, field)
            if isinstance(value, str) and value.strip():
                merged_payload[field] = value

        if improvement_patch.key_features is not None:
            merged_payload["key_features"] = improvement_patch.key_features

        module_patches = {patch.module_id: patch for patch in improvement_patch.modules}
        for module in merged_payload["modules"]:
            patch = module_patches.get(module.get("module_id"))
            if patch is None:
                continue
            if patch.headline:
                module["headline"] = patch.headline
            if patch.body:
                module["body"] = patch.body
            if patch.bullets is not None:
                module["bullets"] = patch.bullets

        return AplusDraftPayload.model_validate(merged_payload)

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

        return OpenAiAplusService._merge_translated_payload(
            original_payload=draft_payload,
            translated_payload=translated_payload,
        )

    @staticmethod
    def _merge_translated_payload(
        *,
        original_payload: AplusDraftPayload,
        translated_payload: dict[str, Any],
    ) -> AplusDraftPayload:
        merged_payload = original_payload.model_dump(mode="json")
        translated_modules = translated_payload.get("modules", [])
        translated_by_id = {
            module.get("module_id"): module
            for module in translated_modules
            if isinstance(module, dict) and isinstance(module.get("module_id"), str)
        }

        for field in ["headline", "subheadline", "brand_story"]:
            value = translated_payload.get(field)
            if isinstance(value, str) and value.strip():
                merged_payload[field] = value

        key_features = translated_payload.get("key_features")
        if isinstance(key_features, list) and all(isinstance(item, str) for item in key_features):
            merged_payload["key_features"] = key_features

        original_modules = merged_payload.get("modules", [])
        for index, original_module in enumerate(original_modules):
            if not isinstance(original_module, dict):
                continue

            translated_module = translated_by_id.get(original_module.get("module_id"))
            if translated_module is None and index < len(translated_modules):
                candidate = translated_modules[index]
                translated_module = candidate if isinstance(candidate, dict) else None
            if translated_module is None:
                continue

            for field in ["headline", "body", "image_brief"]:
                value = translated_module.get(field)
                if isinstance(value, str) and value.strip():
                    original_module[field] = value

            bullets = translated_module.get("bullets")
            if isinstance(bullets, list) and all(isinstance(item, str) for item in bullets):
                original_module["bullets"] = bullets

        return AplusDraftPayload.model_validate(merged_payload)

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
