from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from uuid import uuid4

from app.core.config import Settings
from app.schemas.aplus import AplusDraftPayload
from app.services.aplus_readiness import build_aplus_readiness_report
from app.services.ai.openai_service import OpenAiAplusService
from app.services.aplus_service import AplusService
from app.services.media_storage import MediaStorageService


class FakeSession:
    def __init__(self) -> None:
        self.registry: dict[tuple[str, object], object] = {}

    def get(self, model: object, key: object) -> object | None:
        model_name = getattr(model, "__name__", str(model))
        return self.registry.get((model_name, key))


class StubLiveAdapter:
    def prepare_aplus_content_payload(
        self,
        *,
        asin: str,
        draft_content: dict[str, object],
        marketplace_id: str | None = None,
    ) -> dict[str, object]:
        return {
            "asin": asin,
            "marketplace_id": marketplace_id,
            "draft_content": draft_content,
        }


class StubAmazonService:
    def __init__(self) -> None:
        self.live_adapter = StubLiveAdapter()


def build_publish_product() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        asin="B0PUBLISHTEST",
        title="Publishable Product",
        marketplace_id="A1PA6795UKMFR9",
    )


def build_publish_payload(modules: list[dict[str, object]]) -> AplusDraftPayload:
    return AplusDraftPayload(
        headline="Comfort that converts",
        subheadline="Clear shopper outcomes with structure that stays concise for Amazon modules.",
        brand_story=(
            "This brand story explains the material choice, the intended use context, and the practical "
            "difference versus generic alternatives without relying on vague quality claims."
        ),
        key_features=[
            "Explains the core benefit in shopper language",
            "Clarifies the usage scenario quickly",
            "Shows a clear point of differentiation",
        ],
        modules=modules,
        compliance_notes=[
            "Verify all factual claims before publishing.",
            "Review imagery and overlays for marketplace compliance.",
        ],
    )


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


def test_build_amazon_payload_maps_resolved_module_images() -> None:
    product = build_publish_product()

    with TemporaryDirectory() as tmpdir:
        storage = MediaStorageService(root=Path(tmpdir), url_prefix="/media")
        storage.ensure_directories()
        _, generated_url = storage.store_bytes(
            subdirectory="aplus-assets",
            suffix=".png",
            content=b"\x89PNG\r\n\x1a\ntest-generated",
        )
        _, uploaded_url = storage.store_bytes(
            subdirectory="aplus-assets",
            suffix=".png",
            content=b"\x89PNG\r\n\x1a\ntest-uploaded",
        )
        _, existing_url = storage.store_bytes(
            subdirectory="aplus-assets",
            suffix=".png",
            content=b"\x89PNG\r\n\x1a\ntest-existing",
        )

        existing_asset_id = uuid4()
        session = FakeSession()
        session.registry[("AplusAsset", existing_asset_id)] = SimpleNamespace(
            id=existing_asset_id,
            product_id=product.id,
            public_url=existing_url,
        )

        service = AplusService(
            session,
            StubAmazonService(),  # type: ignore[arg-type]
            None,  # type: ignore[arg-type]
            storage,
        )
        payload = build_publish_payload(
            [
                {
                    "module_type": "hero",
                    "headline": "Hero with image",
                    "body": "Lead with the main benefit and support it with a publishable hero image.",
                    "bullets": ["Comfort first", "Use-case clarity"],
                    "image_brief": "Show the product in realistic use.",
                    "image_mode": "generated",
                    "generated_image_url": generated_url,
                    "overlay_text": "Built for daily comfort",
                },
                {
                    "module_type": "feature",
                    "headline": "Uploaded detail",
                    "body": "Use an uploaded close-up to support the material and fit explanation clearly.",
                    "bullets": ["Close-up detail", "Material benefit"],
                    "image_brief": "Show a close-up detail view.",
                    "image_mode": "uploaded",
                    "uploaded_image_url": uploaded_url,
                },
                {
                    "module_type": "feature",
                    "headline": "Library asset",
                    "body": "Reuse a vetted asset from the product library for a consistent module visual.",
                    "bullets": ["Reusable asset", "Consistent presentation"],
                    "image_brief": "Show the approved brand or product asset.",
                    "image_mode": "existing_asset",
                    "selected_asset_id": str(existing_asset_id),
                    "overlay_text": "Trusted visual",
                },
                {
                    "module_type": "comparison",
                    "headline": "Compared with generic",
                    "body": "Explain the practical advantage against a generic alternative.",
                    "bullets": ["Fit | Tailored support | Basic support"],
                    "image_brief": "Comparison visuals are optional in the editor but not used in publish.",
                },
            ]
        )

        prepared = service._build_amazon_payload(
            product=product,
            draft_payload=payload,
            target_language="de-DE",
        )

    modules = prepared["draft_content"]["contentDocument"]["contentModuleList"]

    assert modules[0]["contentModuleType"] == "STANDARD_HEADER_IMAGE_TEXT"
    assert modules[0]["image"]["assetUrl"] == generated_url
    assert modules[0]["overlayText"] == "Built for daily comfort"
    assert "image_mode" not in modules[0]

    assert modules[1]["contentModuleType"] == "STANDARD_SINGLE_IMAGE_HIGHLIGHTS"
    assert modules[1]["image"]["assetUrl"] == uploaded_url

    assert modules[2]["image"]["assetUrl"] == existing_url
    assert modules[2]["overlayText"] == "Trusted visual"
    assert "selected_asset_id" not in modules[2]

    assert modules[3]["contentModuleType"] == "STANDARD_COMPARISON_TABLE"
    assert "image" not in modules[3]
    assert modules[3]["comparisonRows"][0]["criteria"] == "Fit"


def test_build_amazon_payload_blocks_missing_generated_image() -> None:
    product = build_publish_product()
    service = AplusService(
        FakeSession(),
        StubAmazonService(),  # type: ignore[arg-type]
        None,  # type: ignore[arg-type]
        MediaStorageService(root=Path("/tmp/aplus-test-missing"), url_prefix="/media"),
    )
    payload = build_publish_payload(
        [
            {
                "module_type": "hero",
                "headline": "Hero missing image",
                "body": "The image mode points at generated output, but the actual image is still missing.",
                "bullets": ["Primary benefit", "Customer context"],
                "image_brief": "Show the hero image.",
                "image_mode": "generated",
            },
            {
                "module_type": "feature",
                "headline": "Feature text only",
                "body": "Text-only feature content is still acceptable in the fallback mapping.",
                "bullets": ["Benefit one"],
                "image_brief": "No image required here.",
            },
            {
                "module_type": "comparison",
                "headline": "Comparison block",
                "body": "Show a clear comparison against generic alternatives.",
                "bullets": ["Fit | Tailored support | Basic support"],
                "image_brief": "Comparison image brief.",
            },
        ]
    )

    try:
        service._build_amazon_payload(product=product, draft_payload=payload, target_language="de-DE")
    except ValueError as exc:
        assert "generated image is selected but no generated asset is available" in str(exc)
    else:
        raise AssertionError("Expected missing generated image to block publish payload preparation.")


def test_build_amazon_payload_resolves_existing_asset_scope_safely() -> None:
    product = build_publish_product()
    other_product_id = uuid4()

    with TemporaryDirectory() as tmpdir:
        storage = MediaStorageService(root=Path(tmpdir), url_prefix="/media")
        storage.ensure_directories()
        _, existing_url = storage.store_bytes(
            subdirectory="aplus-assets",
            suffix=".png",
            content=b"\x89PNG\r\n\x1a\nscoped-existing",
        )
        asset_id = uuid4()
        session = FakeSession()
        session.registry[("AplusAsset", asset_id)] = SimpleNamespace(
            id=asset_id,
            product_id=other_product_id,
            public_url=existing_url,
        )

        service = AplusService(
            session,
            StubAmazonService(),  # type: ignore[arg-type]
            None,  # type: ignore[arg-type]
            storage,
        )
        payload = build_publish_payload(
            [
                {
                    "module_type": "hero",
                    "headline": "Scoped asset",
                    "body": "This hero tries to use an asset from a different product scope and should fail.",
                    "bullets": ["Benefit", "Scope"],
                    "image_brief": "Show the selected asset.",
                    "image_mode": "existing_asset",
                    "selected_asset_id": str(asset_id),
                },
                {
                    "module_type": "feature",
                    "headline": "Fallback text",
                    "body": "A second module keeps the draft shape valid for the payload schema.",
                    "bullets": ["Second module"],
                    "image_brief": "Text-only feature image brief.",
                },
                {
                    "module_type": "comparison",
                    "headline": "Comparison block",
                    "body": "Provide a concise comparison body here to satisfy the schema and publish builder.",
                    "bullets": ["Fit | Tailored support | Basic support"],
                    "image_brief": "Comparison image brief.",
                },
            ]
        )

        try:
            service._build_amazon_payload(
                product=product,
                draft_payload=payload,
                target_language="de-DE",
            )
        except ValueError as exc:
            assert "outside the allowed product scope" in str(exc)
        else:
            raise AssertionError("Expected out-of-scope asset usage to fail publish preparation.")


def test_build_amazon_payload_rejects_unsupported_module_image_combinations() -> None:
    product = build_publish_product()

    with TemporaryDirectory() as tmpdir:
        storage = MediaStorageService(root=Path(tmpdir), url_prefix="/media")
        storage.ensure_directories()
        _, uploaded_url = storage.store_bytes(
            subdirectory="aplus-assets",
            suffix=".png",
            content=b"\x89PNG\r\n\x1a\nfaq-uploaded",
        )
        service = AplusService(
            FakeSession(),
            StubAmazonService(),  # type: ignore[arg-type]
            None,  # type: ignore[arg-type]
            storage,
        )
        payload = build_publish_payload(
            [
                {
                    "module_type": "hero",
                    "headline": "Hero text only",
                    "body": "The hero remains valid without an image because the publish mapping falls back safely.",
                    "bullets": ["Value proposition", "Use-case clarity"],
                    "image_brief": "Hero image brief.",
                },
                {
                    "module_type": "faq",
                    "headline": "FAQ with image",
                    "body": "This module incorrectly tries to carry an uploaded image into a text-only module.",
                    "bullets": ["Support answer"],
                    "image_brief": "FAQ image brief.",
                    "image_mode": "uploaded",
                    "uploaded_image_url": uploaded_url,
                    "overlay_text": "This should not publish",
                },
                {
                    "module_type": "comparison",
                    "headline": "Comparison block",
                    "body": "Provide a concise comparison body here to keep the payload shape valid.",
                    "bullets": ["Fit | Tailored support | Basic support"],
                    "image_brief": "Comparison image brief.",
                },
            ]
        )

        try:
            service._build_amazon_payload(
                product=product,
                draft_payload=payload,
                target_language="de-DE",
            )
        except ValueError as exc:
            assert "selected image mode is not supported for this module type" in str(exc)
        else:
            raise AssertionError("Expected unsupported FAQ image usage to fail publish preparation.")
