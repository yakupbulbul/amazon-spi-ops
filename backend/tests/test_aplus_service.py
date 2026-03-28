from app.core.config import Settings
from app.schemas.aplus import AplusDraftPayload
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
