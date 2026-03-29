from app.core.config import Settings
from app.schemas.aplus import AplusDraftPayload
from app.services.aplus_readiness import build_aplus_readiness_report
from app.services.ai.openai_service import OpenAiAplusService


def test_generate_aplus_draft_returns_mock_payload_without_api_key() -> None:
    service = OpenAiAplusService(
        Settings(
            OPENAI_API_KEY="",
            OPENAI_MODEL="gpt-4o-mini",
        )
    )

    draft = service.generate_aplus_draft(
        product_context={
            "title": "Seat Cover",
            "brand": "PYATO",
            "sku": "DF-LPER-Z2CC",
            "asin": "B0GS3SHBNH",
            "marketplace_id": "A1PA6795UKMFR9",
            "price_amount": "29.95",
            "price_currency": "EUR",
            "inventory": {
                "available_quantity": 7,
                "reserved_quantity": 1,
                "inbound_quantity": 0,
            },
        },
        brand_tone="practical and premium",
        positioning="car interior comfort",
        source_language="de-DE",
    )

    assert draft.headline == "Klarer Nutzen. Jeden Tag."
    assert len(draft.key_features) == 4
    assert len(draft.modules) == 5
    assert draft.modules[0].module_type == "hero"
    assert draft.modules[1].module_type == "feature"
    assert draft.modules[2].module_type == "feature"
    assert draft.modules[3].module_type == "comparison"
    assert draft.modules[4].module_type == "faq"
    assert "Seat Cover" in draft.modules[0].body
    assert "generischen Alternativen" in draft.modules[3].body
    assert "Overlay" in draft.modules[0].image_brief


def test_translate_aplus_draft_preserves_schema_shape_without_api_key() -> None:
    service = OpenAiAplusService(
        Settings(
            OPENAI_API_KEY="",
            OPENAI_MODEL="gpt-4o-mini",
        )
    )

    original = service.generate_aplus_draft(
        product_context={
            "title": "Seat Cover",
            "brand": "PYATO",
            "sku": "DF-LPER-Z2CC",
            "asin": "B0GS3SHBNH",
            "marketplace_id": "A1PA6795UKMFR9",
            "price_amount": "29.95",
            "price_currency": "EUR",
            "inventory": {
                "available_quantity": 7,
                "reserved_quantity": 1,
                "inbound_quantity": 0,
            },
        },
        brand_tone="practical and premium",
        positioning="car interior comfort",
        source_language="en-GB",
    )

    translated = service.translate_aplus_draft(
        draft_payload=original,
        source_language="en-GB",
        target_language="de-DE",
    )

    assert translated.modules[0].module_type == original.modules[0].module_type
    assert translated.headline.endswith("(de-DE)")


def test_translation_merge_preserves_control_fields_for_image_enabled_modules() -> None:
    original = AplusDraftPayload(
        headline="Original headline",
        subheadline="Original subheadline with clear shopper context.",
        brand_story="Original brand story with product detail, context, and differentiation for editing.",
        key_features=[
            "Original feature one",
            "Original feature two",
            "Original feature three",
        ],
        modules=[
            {
                "module_id": "hero-module-0001",
                "module_type": "hero",
                "headline": "Original hero",
                "body": "Original hero body with a practical customer outcome explained clearly.",
                "bullets": ["Original bullet one", "Original bullet two"],
                "image_brief": "Original image brief with overlay suggestion.",
                "image_mode": "generated",
                "image_prompt": "Keep the original image prompt",
                "generated_image_url": "https://example.com/generated.png",
                "uploaded_image_url": "https://example.com/uploaded.png",
                "selected_asset_id": "asset-12345",
                "reference_asset_ids": ["asset-ref-1", "asset-ref-2"],
                "overlay_text": "Keep this overlay exactly",
                "image_status": "completed",
                "image_error_message": "Preserve exact worker message",
            },
            {
                "module_id": "feature-module-0001",
                "module_type": "feature",
                "headline": "Original feature",
                "body": "Original feature body with a specific shopper benefit.",
                "bullets": ["Original feature bullet"],
                "image_brief": "Original feature image brief.",
            },
            {
                "module_id": "comparison-module-0001",
                "module_type": "comparison",
                "headline": "Original comparison",
                "body": "Original comparison body against generic alternatives.",
                "bullets": ["Fit | Tailored support | Basic support"],
                "image_brief": "Original comparison image brief.",
            },
        ],
        compliance_notes=[
            "Do not translate this internal editorial note.",
            "Preserve the original compliance instruction.",
        ],
    )

    translated = OpenAiAplusService._merge_translated_payload(
        original_payload=original,
        translated_payload={
                "headline": "Translated headline",
                "subheadline": "Translated subheadline",
                "brand_story": "Translated brand story with enough detail to satisfy the schema length requirement safely.",
            "key_features": ["Translated feature one", "Translated feature two", "Translated feature three"],
            "compliance_notes": ["Changed note should not be used"],
            "modules": [
                {
                    "module_id": "hero-module-0001",
                    "module_type": "faq",
                    "headline": "Translated hero",
                    "body": "Translated hero body",
                    "bullets": ["Translated bullet one", "Translated bullet two"],
                    "image_brief": "Translated image brief",
                    "image_mode": "uploaded",
                    "image_prompt": "Changed prompt should be ignored",
                    "generated_image_url": "https://malicious.example/override.png",
                    "uploaded_image_url": "https://malicious.example/override-upload.png",
                    "selected_asset_id": "other-asset",
                    "reference_asset_ids": ["other-ref"],
                    "overlay_text": "Changed overlay should be ignored",
                    "image_status": "failed",
                    "image_error_message": "Changed status should be ignored",
                }
            ],
        },
    )

    translated_hero = translated.modules[0]

    assert translated.headline == "Translated headline"
    assert translated.subheadline == "Translated subheadline"
    assert translated.key_features[0] == "Translated feature one"
    assert translated.compliance_notes == original.compliance_notes
    assert translated_hero.module_type == "hero"
    assert translated_hero.image_mode == "generated"
    assert translated_hero.image_prompt == "Keep the original image prompt"
    assert translated_hero.generated_image_url == "https://example.com/generated.png"
    assert translated_hero.uploaded_image_url == "https://example.com/uploaded.png"
    assert translated_hero.selected_asset_id == "asset-12345"
    assert translated_hero.reference_asset_ids == ["asset-ref-1", "asset-ref-2"]
    assert translated_hero.overlay_text == "Keep this overlay exactly"
    assert translated_hero.image_status == "completed"
    assert translated_hero.image_error_message == "Preserve exact worker message"


def test_multilingual_mock_generation_varies_by_locale_and_structure() -> None:
    service = OpenAiAplusService(
        Settings(
            OPENAI_API_KEY="",
            OPENAI_MODEL="gpt-4o-mini",
        )
    )

    de_draft = service.generate_aplus_draft(
        product_context={
            "title": "Trail Backpack",
            "brand": "Nordvale",
            "sku": "TRAIL-42",
            "asin": "B0TESTDE01",
            "marketplace_id": "A1PA6795UKMFR9",
        },
        brand_tone="premium and technical",
        positioning="commuters and day-hike users",
        source_language="de-DE",
    )
    en_draft = service.generate_aplus_draft(
        product_context={
            "title": "Trail Backpack",
            "brand": "Nordvale",
            "sku": "TRAIL-42",
            "asin": "B0TESTEN01",
            "marketplace_id": "A1F83G8C2ARO7P",
        },
        brand_tone="premium and technical",
        positioning="commuters and day-hike users",
        source_language="en-GB",
    )

    assert de_draft.headline != en_draft.headline
    assert "generischen Alternativen" in de_draft.modules[3].body
    assert "generic alternatives" in en_draft.modules[3].body
    assert any("Overlay" in module.image_brief for module in de_draft.modules)
    assert any("overlay text" in module.image_brief for module in en_draft.modules)


def test_aplus_structured_output_schema_requires_all_module_fields() -> None:
    schema = AplusDraftPayload.model_json_schema()
    module_schema = schema["$defs"]["AplusModulePayload"]

    assert module_schema["additionalProperties"] is False
    assert set(module_schema["required"]) == {
        "module_type",
        "headline",
        "body",
        "bullets",
        "image_brief",
    }


def test_publish_readiness_report_flags_blockers_and_warnings() -> None:
    payload = AplusDraftPayload(
        headline="The best choice for every drive",
        subheadline="Premium quality comfort that feels perfect on every trip without compromise.",
        brand_story=(
            "This premium quality seat cover is the best option for every driver and delivers premium "
            "quality comfort that works great for everyday use across every routine."
        ),
        key_features=[
            "Premium quality materials for everyday use",
            "Premium quality materials for everyday use",
            "Great for everyday use",
        ],
        modules=[
            {
                "module_type": "hero",
                "headline": "Premium quality comfort",
                "body": "Premium quality comfort for every ride and great for everyday use.",
                "bullets": [
                    "Premium quality materials for everyday use",
                    "Premium quality materials for everyday use",
                ],
                "image_brief": "Show the product in use with a premium quality overlay for everyday comfort.",
            },
            {
                "module_type": "feature",
                "headline": "Great for everyday use",
                "body": "Great for everyday use and premium quality comfort in every setting.",
                "bullets": [
                    "Great for everyday use",
                ],
                "image_brief": "Use a generic comfort visual.",
            },
            {
                "module_type": "feature",
                "headline": "Premium quality comfort",
                "body": "Premium quality comfort for every ride and great for everyday use.",
                "bullets": [
                    "Great for everyday use",
                ],
                "image_brief": "Use a generic comfort visual.",
            },
        ],
        compliance_notes=[
            "Verify claims before publishing.",
            "Review visual guidance before launch.",
        ],
    )

    report = build_aplus_readiness_report(
        draft_payload=payload,
        checked_payload="validated",
    )

    assert report.is_publish_ready is False
    assert "Comparison section" in report.missing_sections
    assert any(issue.code == "unsupported_claim" for issue in report.blocking_errors)
    assert any(issue.code == "missing_comparison" for issue in report.blocking_errors)
    assert any(issue.code == "repeated_copy" for issue in report.warnings)
    assert any(issue.code == "vague_claim" for issue in report.warnings)


def test_mock_generation_is_publish_ready_under_new_readiness_rules() -> None:
    generator = OpenAiAplusService(
        Settings(
            OPENAI_API_KEY="",
            OPENAI_MODEL="gpt-4o-mini",
        )
    )

    draft = generator.generate_aplus_draft(
        product_context={
            "title": "Trail Backpack",
            "brand": "Nordvale",
            "sku": "TRAIL-42",
            "asin": "B0TESTEN01",
            "marketplace_id": "A1F83G8C2ARO7P",
        },
        brand_tone="premium and technical",
        positioning="commuters and day-hike users",
        source_language="en-GB",
    )

    report = build_aplus_readiness_report(
        draft_payload=draft,
        checked_payload="draft",
    )

    assert report.is_publish_ready is True
    assert report.blocking_errors == []
