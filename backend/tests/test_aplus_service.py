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

    assert draft.headline == "PYATO presentation for Seat Cover (de-DE)"
    assert len(draft.key_features) == 3
    assert len(draft.modules) == 3
    assert draft.modules[0].module_type == "hero"
    assert "Seat Cover" in draft.modules[0].body


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
