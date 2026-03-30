from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from uuid import uuid4

from app.core.config import Settings
from app.schemas.aplus import AplusDraftPayload
from app.services.aplus_optimization import build_aplus_optimization_report
from app.services.aplus_readiness import build_aplus_readiness_report
from app.services.ai.openai_service import OpenAiAplusService
from app.services.aplus_service import AplusService
from app.services.media_storage import MediaStorageService


class FakeSession:
    def __init__(self) -> None:
        self.registry: dict[tuple[str, object], object] = {}
        self.added: list[object] = []

    def get(self, model: object, key: object) -> object | None:
        model_name = getattr(model, "__name__", str(model))
        return self.registry.get((model_name, key))

    def add(self, obj: object) -> None:
        model_name = type(obj).__name__
        if getattr(obj, "id", None) is None:
            obj.id = uuid4()
        if getattr(obj, "created_at", None) is None:
            obj.created_at = datetime.now(timezone.utc)
        if getattr(obj, "updated_at", None) is None:
            obj.updated_at = obj.created_at
        self.registry[(model_name, obj.id)] = obj
        self.added.append(obj)

    def commit(self) -> None:
        for obj in self.added:
            if getattr(obj, "updated_at", None) is None:
                obj.updated_at = datetime.now(timezone.utc)
        return None

    def refresh(self, obj: object) -> None:
        model_name = type(obj).__name__
        self.registry[(model_name, obj.id)] = obj

    def flush(self) -> None:
        return None


class StubTranslationOpenAi:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def translate_aplus_draft(
        self,
        *,
        draft_payload: AplusDraftPayload,
        source_language: str,
        target_language: str,
    ) -> AplusDraftPayload:
        self.calls.append((source_language, target_language))
        payload = draft_payload.model_copy(deep=True)
        payload.headline = f"Recovered {target_language} draft"
        return payload


class StubAmazonService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def create_aplus_upload_destination(
        self,
        *,
        marketplace_id: str | None,
        content_md5: str,
        content_type: str,
    ) -> dict[str, object]:
        self.calls.append(("create_aplus_upload_destination", marketplace_id, content_type))
        return {
            "payload": {
                "uploadDestinationId": f"upload-{content_type.split('/')[-1]}",
                "url": "https://example.com/upload",
                "headers": {
                    "key": "aplus/mock-key",
                    "policy": "mock-policy",
                },
            }
        }

    def upload_asset_to_destination(
        self,
        *,
        url: str,
        form_fields: dict[str, object],
        file_name: str,
        content: bytes,
        content_type: str,
    ) -> None:
        self.calls.append(("upload_asset_to_destination", file_name, content_type, len(content)))

    def validate_aplus_content_document(
        self,
        *,
        marketplace_id: str | None,
        asin_set: list[str],
        document_request: dict[str, object],
    ) -> dict[str, object]:
        self.calls.append(("validate_aplus_content_document", marketplace_id, asin_set, document_request))
        return {"warnings": [], "errors": []}

    def create_aplus_content_document(
        self,
        *,
        marketplace_id: str | None,
        document_request: dict[str, object],
    ) -> dict[str, object]:
        self.calls.append(("create_aplus_content_document", marketplace_id, document_request))
        return {"warnings": [], "contentReferenceKey": "REF-123"}

    def post_aplus_content_document_asin_relations(
        self,
        *,
        marketplace_id: str | None,
        content_reference_key: str,
        asin_set: list[str],
    ) -> dict[str, object]:
        self.calls.append(("post_aplus_content_document_asin_relations", content_reference_key, asin_set))
        return {"warnings": []}

    def submit_aplus_content_document_for_approval(
        self,
        *,
        marketplace_id: str | None,
        content_reference_key: str,
    ) -> dict[str, object]:
        self.calls.append(("submit_aplus_content_document_for_approval", content_reference_key))
        return {"warnings": []}

    def get_aplus_content_document(
        self,
        *,
        marketplace_id: str | None,
        content_reference_key: str,
        included_data_set: list[str],
    ) -> dict[str, object]:
        self.calls.append(("get_aplus_content_document", content_reference_key, included_data_set))
        return {
            "warnings": [],
            "contentRecord": {
                "contentReferenceKey": content_reference_key,
                "contentMetadata": {
                    "name": "Publishable Product A+ Content",
                    "marketplaceId": marketplace_id,
                    "status": "SUBMITTED",
                    "badgeSet": [],
                    "updateTime": "2026-03-29T00:00:00Z",
                },
            },
        }


class ApprovedAmazonService(StubAmazonService):
    def get_aplus_content_document(
        self,
        *,
        marketplace_id: str | None,
        content_reference_key: str,
        included_data_set: list[str],
    ) -> dict[str, object]:
        return {
            "warnings": [{"message": "Awaiting moderation replication"}],
            "contentRecord": {
                "contentReferenceKey": content_reference_key,
                "contentMetadata": {
                    "name": "Publishable Product A+ Content",
                    "marketplaceId": marketplace_id,
                    "status": "APPROVED",
                    "badgeSet": [],
                    "updateTime": "2026-03-29T00:00:00Z",
                },
            },
        }


class RejectedAmazonService(StubAmazonService):
    def get_aplus_content_document(
        self,
        *,
        marketplace_id: str | None,
        content_reference_key: str,
        included_data_set: list[str],
    ) -> dict[str, object]:
        return {
            "warnings": [],
            "errors": [
                {"message": "Image crop does not match the supported module requirements."},
                {"message": "Hero alt text exceeds the approved length."},
            ],
            "contentRecord": {
                "contentReferenceKey": content_reference_key,
                "contentMetadata": {
                    "name": "Publishable Product A+ Content",
                    "marketplaceId": marketplace_id,
                    "status": "REJECTED",
                    "badgeSet": [],
                    "updateTime": "2026-03-29T00:00:00Z",
                },
            },
        }


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
    schema = OpenAiAplusService._openai_response_schema()
    module_schema = schema["$defs"]["AplusModulePayload"]

    assert module_schema["additionalProperties"] is False
    assert set(module_schema["required"]) == {
        "module_id",
        "module_type",
        "headline",
        "body",
        "bullets",
        "image_brief",
        "image_mode",
        "image_prompt",
        "generated_image_url",
        "uploaded_image_url",
        "selected_asset_id",
        "reference_asset_ids",
        "overlay_text",
        "image_status",
        "image_error_message",
        "image_request_fingerprint",
    }


def test_openai_response_schema_requires_every_property_recursively() -> None:
    schema = OpenAiAplusService._openai_response_schema()

    def assert_required_alignment(node: object) -> None:
        if isinstance(node, dict):
            properties = node.get("properties")
            if isinstance(properties, dict) and properties:
                assert set(node.get("required", [])) == set(properties.keys())
            for value in node.values():
                assert_required_alignment(value)
            return

        if isinstance(node, list):
            for item in node:
                assert_required_alignment(item)

    assert_required_alignment(schema)


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
    assert any(issue.code == "unsupported_claim" for issue in report.blocking_errors)
    assert any(issue.code == "missing_required_publish_image" for issue in report.blocking_errors)
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

    assert report.is_publish_ready is False
    assert any(issue.code == "unsupported_module_type" for issue in report.blocking_errors)


def test_recover_source_variant_creates_original_sibling_for_translated_only_draft() -> None:
    product_id = uuid4()
    draft_id = uuid4()
    product = SimpleNamespace(
        id=product_id,
        sku="DOG-SEAT-COVER",
        asin="B0DOGTEST01",
        title="Dog Seat Cover",
        marketplace_id="A1PA6795UKMFR9",
        aplus_drafts=[],
    )
    translated_payload = AplusDraftPayload.model_validate(
        {
            "headline": "Recovered translated draft",
            "subheadline": "Keep the translated structure available for editing.",
            "brand_story": "This translated variant is the only stored draft and needs a source sibling so editors can switch languages safely.",
            "key_features": [
                "Waterproof layer",
                "Non-slip anchor points",
                "Fast clean-up after travel",
            ],
            "modules": [
                {
                    "module_id": "hero-module-1",
                    "module_type": "hero",
                    "headline": "Travel without mess",
                    "body": "Protect the rear bench while keeping setup and clean-up practical for everyday use.",
                    "bullets": ["Waterproof barrier", "Quick install"],
                    "image_brief": "Show the rear seat cover in realistic daily use.",
                },
                {
                    "module_id": "feature-module-1",
                    "module_type": "feature",
                    "headline": "Grip that stays put",
                    "body": "Explain how the anchors and backing reduce shifting during driving.",
                    "bullets": ["Anchored corners", "Stable backing"],
                    "image_brief": "Show a close-up of the anchor system.",
                },
                {
                    "module_id": "faq-module-1",
                    "module_type": "faq",
                    "headline": "Built for routine trips",
                    "body": "Use the FAQ module to reassure shoppers about cleaning and daily use expectations.",
                    "bullets": [],
                    "image_brief": "No image required.",
                },
            ],
            "compliance_notes": [
                "Avoid unsupported safety claims.",
                "Keep usage guidance practical and clear.",
            ],
        }
    )
    translated_draft = SimpleNamespace(
        id=draft_id,
        product_id=product_id,
        status="draft",
        brand_tone="Practical and reassuring.",
        positioning="Dog owners who travel weekly.",
        variant_group_id="variant-group-1",
        variant_role="translated",
        source_language="de-DE",
        target_language="en-GB",
        auto_translate=True,
        draft_payload=translated_payload.model_dump(mode="json"),
        validated_payload=None,
        created_by_id=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    product.aplus_drafts.append(translated_draft)

    session = FakeSession()
    session.registry[("Product", product_id)] = product
    session.registry[("AplusDraft", draft_id)] = translated_draft
    openai_service = StubTranslationOpenAi()
    service = AplusService(
        session,
        StubAmazonService(),  # type: ignore[arg-type]
        openai_service,  # type: ignore[arg-type]
        MediaStorageService(root=Path("/tmp/aplus-test-recover"), url_prefix="/media"),
    )

    recovered = service.recover_source_variant(draft_id=draft_id)

    assert recovered.variant_role == "original"
    assert recovered.source_language == "de-DE"
    assert recovered.target_language == "de-DE"
    assert recovered.product_id == str(product_id)
    assert openai_service.calls == [("en-GB", "de-DE")]
    assert len(product.aplus_drafts) == 2



def test_publish_to_amazon_maps_supported_subset_and_runs_real_stage_order() -> None:
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
        session = FakeSession()
        generated_asset_id = uuid4()
        session.registry[("AplusAsset", generated_asset_id)] = SimpleNamespace(
            id=generated_asset_id,
            product_id=product.id,
            asset_metadata={},
            file_name="generated.png",
            mime_type="image/png",
            public_url=generated_url,
        )
        uploaded_asset_id = uuid4()
        session.registry[("AplusAsset", uploaded_asset_id)] = SimpleNamespace(
            id=uploaded_asset_id,
            product_id=product.id,
            asset_metadata={},
            file_name="uploaded.png",
            mime_type="image/png",
            public_url=uploaded_url,
        )

        amazon_service = StubAmazonService()
        service = AplusService(
            session,
            amazon_service,  # type: ignore[arg-type]
            None,  # type: ignore[arg-type]
            storage,
        )
        service._read_image_dimensions = staticmethod(  # type: ignore[method-assign]
            lambda *, content, expected_mime_type, field_label: (1200, 800)
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
                    "selected_asset_id": str(generated_asset_id),
                },
                {
                    "module_type": "feature",
                    "headline": "Uploaded detail",
                    "body": "Use an uploaded close-up to support the material and fit explanation clearly.",
                    "bullets": ["Close-up detail", "Material benefit"],
                    "image_brief": "Show a close-up detail view.",
                    "image_mode": "uploaded",
                    "uploaded_image_url": uploaded_url,
                    "selected_asset_id": str(uploaded_asset_id),
                },
                {
                    "module_type": "faq",
                    "headline": "Library asset",
                    "body": "Reuse a vetted asset from the product library for a consistent reassurance module without unsupported image fields.",
                    "bullets": ["Reusable asset", "Consistent presentation"],
                    "image_brief": "No image required for faq.",
                },
            ]
        )

        prepared = service._publish_to_amazon(
            product=product,
            draft_payload=payload,
            target_language="de-DE",
        )

    modules = prepared["contentDocumentRequest"]["contentDocument"]["contentModuleList"]

    assert prepared["contentReferenceKey"] == "REF-123"
    assert modules[0]["contentModuleType"] == "STANDARD_HEADER_IMAGE_TEXT"
    assert (
        modules[0]["standardHeaderImageText"]["block"]["image"]["uploadDestinationId"]
        == "upload-png"
    )
    assert modules[1]["contentModuleType"] == "STANDARD_SINGLE_IMAGE_HIGHLIGHTS"
    assert modules[2]["contentModuleType"] == "STANDARD_TEXT"
    assert prepared["contentRecord"]["contentMetadata"]["status"] == "SUBMITTED"
    assert [call[0] for call in amazon_service.calls] == [
        "create_aplus_upload_destination",
        "upload_asset_to_destination",
        "create_aplus_upload_destination",
        "upload_asset_to_destination",
        "validate_aplus_content_document",
        "create_aplus_content_document",
        "post_aplus_content_document_asin_relations",
        "submit_aplus_content_document_for_approval",
        "get_aplus_content_document",
    ]


def test_publish_to_amazon_truncates_publish_alt_text_to_amazon_limit() -> None:
    product = build_publish_product()

    with TemporaryDirectory() as tmpdir:
        storage = MediaStorageService(root=Path(tmpdir), url_prefix="/media")
        storage.ensure_directories()
        _, generated_url = storage.store_bytes(
            subdirectory="aplus-assets",
            suffix=".png",
            content=b"\x89PNG\r\n\x1a\ntest-generated",
        )
        session = FakeSession()
        generated_asset_id = uuid4()
        session.registry[("AplusAsset", generated_asset_id)] = SimpleNamespace(
            id=generated_asset_id,
            product_id=product.id,
            asset_metadata={},
            file_name="generated.png",
            mime_type="image/png",
            public_url=generated_url,
        )

        amazon_service = StubAmazonService()
        service = AplusService(
            session,
            amazon_service,  # type: ignore[arg-type]
            None,  # type: ignore[arg-type]
            storage,
        )
        service._read_image_dimensions = staticmethod(  # type: ignore[method-assign]
            lambda *, content, expected_mime_type, field_label: (1200, 800)
        )
        payload = build_publish_payload(
            [
                {
                    "module_type": "hero",
                    "headline": "Hero with image",
                    "body": "Lead with the main benefit and support it with a publishable hero image.",
                    "bullets": ["Comfort first", "Use-case clarity"],
                    "image_brief": (
                        "Show the product in a clean daily-use scene with realistic scale, "
                        "clear material detail, and an overlay-ready comfort message for shoppers."
                    ),
                    "image_mode": "generated",
                    "generated_image_url": generated_url,
                    "selected_asset_id": str(generated_asset_id),
                },
                {
                    "module_type": "feature",
                    "headline": "Feature detail",
                    "body": "Use a supporting close-up for the secondary module.",
                    "bullets": ["Benefit one", "Benefit two"],
                    "image_brief": "Show a close-up detail view.",
                    "image_mode": "generated",
                    "generated_image_url": generated_url,
                    "selected_asset_id": str(generated_asset_id),
                },
                {
                    "module_type": "faq",
                    "headline": "Trust block",
                    "body": "Plain text reassurance keeps the supported subset valid.",
                    "bullets": [],
                    "image_brief": "No image required.",
                },
            ]
        )

        service._publish_to_amazon(product=product, draft_payload=payload, target_language="de-DE")

    validate_call = next(call for call in amazon_service.calls if call[0] == "validate_aplus_content_document")
    modules = validate_call[3]["contentDocument"]["contentModuleList"]
    hero_alt_text = modules[0]["standardHeaderImageText"]["block"]["image"]["altText"]
    assert len(hero_alt_text) <= 100
    assert hero_alt_text.startswith("Show the product in a clean daily-use scene")


def test_publish_to_amazon_blocks_missing_generated_image_asset() -> None:
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
                "headline": "Feature image required",
                "body": "This supported feature also expects a prepared image asset for the real Amazon contract.",
                "bullets": ["Benefit one", "Benefit two"],
                "image_brief": "Feature image brief.",
                "image_mode": "generated",
            },
            {
                "module_type": "faq",
                "headline": "Trust block",
                "body": "Plain text reassurance keeps the supported subset valid while the image is still missing.",
                "bullets": [],
                "image_brief": "No image required.",
            },
        ]
    )

    try:
        service._publish_to_amazon(product=product, draft_payload=payload, target_language="de-DE")
    except ValueError as exc:
        assert "missing its selected local image before Amazon publish" in str(exc)
    else:
        raise AssertionError("Expected missing generated image to block real publish.")


def test_publish_to_amazon_resolves_existing_asset_scope_safely() -> None:
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
            asset_metadata={},
            file_name="scoped.png",
            mime_type="image/png",
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
                    "headline": "Second supported image module",
                    "body": "A second supported image module keeps the payload shape realistic for the Amazon contract.",
                    "bullets": ["Second module", "Second benefit"],
                    "image_brief": "Text-only feature image brief.",
                    "image_mode": "existing_asset",
                    "selected_asset_id": str(asset_id),
                },
                {
                    "module_type": "faq",
                    "headline": "Trust block",
                    "body": "A text-only trust block keeps the supported module subset intact.",
                    "bullets": [],
                    "image_brief": "No image required.",
                },
            ]
        )

        try:
            service._publish_to_amazon(
                product=product,
                draft_payload=payload,
                target_language="de-DE",
            )
        except ValueError as exc:
            assert "outside the allowed product scope" in str(exc)
        else:
            raise AssertionError("Expected out-of-scope asset usage to fail publish preparation.")


def test_publish_to_amazon_rejects_editorial_only_modules() -> None:
    product = build_publish_product()
    with TemporaryDirectory() as tmpdir:
        storage = MediaStorageService(root=Path(tmpdir), url_prefix="/media")
        storage.ensure_directories()
        _, hero_url = storage.store_bytes(
            subdirectory="aplus-assets",
            suffix=".png",
            content=b"\x89PNG\r\n\x1a\nhero-valid",
        )
        asset_id = uuid4()
        session = FakeSession()
        session.registry[("AplusAsset", asset_id)] = SimpleNamespace(
            id=asset_id,
            product_id=product.id,
            asset_metadata={},
            file_name="hero-valid.png",
            mime_type="image/png",
            public_url=hero_url,
        )

        service = AplusService(
            session,
            StubAmazonService(),  # type: ignore[arg-type]
            None,  # type: ignore[arg-type]
            storage,
        )
        service._read_image_dimensions = staticmethod(  # type: ignore[method-assign]
            lambda *, content, expected_mime_type, field_label: (1200, 800)
        )
        payload = build_publish_payload(
            [
                {
                    "module_type": "hero",
                    "headline": "Hero module",
                    "body": "The hero is otherwise valid, but the comparison block below should still stop real publish.",
                    "bullets": ["Value proposition", "Use-case clarity"],
                    "image_brief": "Hero image brief.",
                    "image_mode": "generated",
                    "generated_image_url": hero_url,
                    "selected_asset_id": str(asset_id),
                },
                {
                    "module_type": "comparison",
                    "headline": "Comparison block",
                    "body": "Comparison remains editorial-only until the exact Amazon comparison contract is implemented.",
                    "bullets": ["Fit | Tailored support | Basic support"],
                    "image_brief": "Comparison image brief.",
                },
                {
                    "module_type": "faq",
                    "headline": "Trust block",
                    "body": "A plain text module is still supported, but the comparison block must fail the real publish subset.",
                    "bullets": [],
                    "image_brief": "No image required.",
                },
            ]
        )

        try:
            service._publish_to_amazon(
                product=product,
                draft_payload=payload,
                target_language="de-DE",
            )
        except ValueError as exc:
            assert "Unsupported modules present: comparison" in str(exc)
        else:
            raise AssertionError("Expected editorial-only comparison modules to block real publish.")


def test_prepare_amazon_asset_reuses_cached_upload_reference_without_reupload() -> None:
    product = build_publish_product()

    with TemporaryDirectory() as tmpdir:
        storage = MediaStorageService(root=Path(tmpdir), url_prefix="/media")
        storage.ensure_directories()
        _, existing_url = storage.store_bytes(
            subdirectory="aplus-assets",
            suffix=".png",
            content=b"\x89PNG\r\n\x1a\ncached-upload",
        )
        asset_id = uuid4()
        session = FakeSession()
        session.registry[("AplusAsset", asset_id)] = SimpleNamespace(
            id=asset_id,
            product_id=product.id,
            asset_metadata={
                "amazon_uploads": {
                    product.marketplace_id: {
                        "upload_destination_id": "sc/existing-upload.png",
                        "width_pixels": 1200,
                        "height_pixels": 700,
                        "crop_width_pixels": 1132,
                        "crop_height_pixels": 700,
                        "crop_offset_x_pixels": 34,
                        "crop_offset_y_pixels": 0,
                    }
                }
            },
            file_name="cached.png",
            mime_type="image/png",
            public_url=existing_url,
        )

        amazon_service = StubAmazonService()
        service = AplusService(
            session,
            amazon_service,  # type: ignore[arg-type]
            None,  # type: ignore[arg-type]
            storage,
        )
        module = AplusDraftPayload.model_validate(
            {
                "headline": "Comfort that converts",
                "subheadline": "Clear benefits that stay concise for the supported Amazon modules.",
                "brand_story": "The brand story explains materials, usage context, and the practical reason this product feels different from generic alternatives.",
                "key_features": [
                    "Explains the benefit in shopper language",
                    "Clarifies the day-to-day use case",
                    "Makes the point of difference concrete",
                ],
                "modules": [
                    {
                        "module_id": "hero-module-1001",
                        "module_type": "hero",
                        "headline": "Daily comfort without bulk",
                        "body": "The hero section explains the main shopper outcome clearly and keeps the promise grounded in daily use.",
                        "bullets": ["Comfort first", "Use-case clarity"],
                        "image_brief": "Show the product in realistic use.",
                        "image_mode": "existing_asset",
                        "selected_asset_id": str(asset_id),
                    },
                    {
                        "module_id": "faq-module-1001",
                        "module_type": "faq",
                        "headline": "Built for everyday use",
                        "body": "Use this text block to reassure shoppers about the intended usage context, care expectations, and practical ownership details.",
                        "bullets": [],
                        "image_brief": "No image required."
                    },
                    {
                        "module_id": "feature-module-1001",
                        "module_type": "feature",
                        "headline": "Why the fit matters",
                        "body": "Explain how the tailored fit improves comfort, reduces bunching, and keeps the product easier to use every day.",
                        "bullets": ["Stays smoother during daily movement", "Reduces extra adjustment during setup"],
                        "image_brief": "Show a close-up detail view.",
                        "image_mode": "none"
                    }
                ],
                "compliance_notes": [
                    "Verify all factual claims before publish.",
                    "Check imagery and image text before submission."
                ]
            }
        ).modules[0]

        prepared_asset = service._ensure_amazon_asset_ready(
            asset=session.registry[("AplusAsset", asset_id)],
            module=module,
            marketplace_id=product.marketplace_id,
        )

    assert prepared_asset.upload_destination_id == "sc/existing-upload.png"
    assert prepared_asset.crop_width_pixels == 1132
    assert [call[0] for call in amazon_service.calls] == []


def test_refresh_publish_job_status_marks_approved_jobs_and_serializes_warnings() -> None:
    product = build_publish_product()
    draft_id = uuid4()
    session = FakeSession()
    session.registry[("Product", product.id)] = product
    service = AplusService(
        session,
        ApprovedAmazonService(),  # type: ignore[arg-type]
        None,  # type: ignore[arg-type]
        MediaStorageService(root=Path("/tmp/aplus-status"), url_prefix="/media"),
    )
    draft = SimpleNamespace(product_id=product.id, status="ready_to_publish")
    publish_job = SimpleNamespace(
        id=uuid4(),
        draft_id=draft_id,
        status="submitted",
        external_submission_id="REF-123",
        response_payload={},
        error_message=None,
        submitted_at=None,
        completed_at=None,
        created_at=service._now(),
    )

    service._refresh_publish_job_status(draft=draft, publish_job=publish_job)
    serialized = service._serialize_publish_job(publish_job)

    assert publish_job.status == "approved"
    assert draft.status == "published"
    assert serialized.warnings == ["Awaiting moderation replication"]


def test_refresh_publish_job_status_marks_rejected_jobs_and_keeps_amazon_reasons() -> None:
    product = build_publish_product()
    session = FakeSession()
    session.registry[("Product", product.id)] = product
    service = AplusService(
        session,
        RejectedAmazonService(),  # type: ignore[arg-type]
        None,  # type: ignore[arg-type]
        MediaStorageService(root=Path("/tmp/aplus-status-rejected"), url_prefix="/media"),
    )
    draft = SimpleNamespace(product_id=product.id, status="ready_to_publish")
    publish_job = SimpleNamespace(
        id=uuid4(),
        draft_id=uuid4(),
        status="submitted",
        external_submission_id="REF-REJECTED",
        response_payload={"validationResponse": {"warnings": []}},
        error_message=None,
        submitted_at=service._now(),
        completed_at=None,
        created_at=service._now(),
    )

    service._refresh_publish_job_status(draft=draft, publish_job=publish_job)
    serialized = service._serialize_publish_job(publish_job)

    assert publish_job.status == "rejected"
    assert draft.status == "failed"
    assert publish_job.error_message == "Image crop does not match the supported module requirements.; Hero alt text exceeds the approved length."
    assert serialized.rejection_reasons == [
        "Image crop does not match the supported module requirements.; Hero alt text exceeds the approved length."
    ]


def test_generate_draft_creates_original_and_translated_variants() -> None:
    from app.models.entities import Product

    db_session = FakeSession()
    product = Product(
        id=uuid4(),
        sku="DF-LPER-Z2CC",
        asin="B0GS3SHBNH",
        title="Seat Cover",
        brand="PYATO",
        marketplace_id="A1PA6795UKMFR9",
        low_stock_threshold=10,
        is_active=True,
    )
    db_session.registry[("Product", product.id)] = product

    service = AplusService(
        db_session,
        StubAmazonService(),
        OpenAiAplusService(Settings(OPENAI_API_KEY="", OPENAI_MODEL="gpt-4o-mini")),
    )
    service._build_product_context = lambda *, product: {
        "title": product.title,
        "brand": product.brand,
        "sku": product.sku,
        "asin": product.asin,
        "marketplace_id": product.marketplace_id,
        "inventory": None,
    }

    response = service.generate_draft(
        product_id=product.id,
        brand_tone="practical and premium",
        positioning="car interior comfort",
        source_language="de-DE",
        target_language="en-GB",
        auto_translate=True,
        requested_by=SimpleNamespace(id=uuid4()),
    )

    stored_drafts = [item for item in db_session.added if type(item).__name__ == "AplusDraft"]

    assert len(stored_drafts) == 2
    assert {draft.variant_role for draft in stored_drafts} == {"original", "translated"}
    assert len({draft.variant_group_id for draft in stored_drafts}) == 1
    assert response.variant_role == "translated"
    assert response.target_language == "en-GB"


def test_save_draft_refreshes_working_payload_and_optimization_state() -> None:
    original_payload = build_publish_payload(
        [
            {
                "module_type": "hero",
                "headline": "Hero promise",
                "body": "A concrete hero body that explains the main shopper outcome in a grounded way.",
                "bullets": ["Primary benefit", "Secondary reassurance"],
                "image_brief": "Hero image direction for publish testing.",
            },
            {
                "module_type": "feature",
                "headline": "Feature detail",
                "body": "Specific supporting body copy with practical detail and clear usage context.",
                "bullets": ["Practical use case", "Material detail"],
                "image_brief": "Feature image direction for publish testing.",
            },
            {
                "module_type": "faq",
                "headline": "Confidence builder",
                "body": "Answers a final shopper hesitation with concrete reassurance and clear next-step context.",
                "bullets": ["Clear reassurance"],
                "image_brief": "FAQ image direction for publish testing.",
            },
        ]
    )
    improved_payload = original_payload.model_copy(
        update={"headline": "Sharper shopper outcome headline"},
        deep=True,
    )

    draft_id = uuid4()
    product_id = uuid4()
    draft = SimpleNamespace(
        id=draft_id,
        product_id=product_id,
        variant_group_id=str(uuid4()),
        variant_role="original",
        status="ready_to_publish",
        brand_tone="practical and premium",
        positioning="car interior comfort",
        source_language="de-DE",
        target_language="de-DE",
        auto_translate=False,
        draft_payload=original_payload.model_dump(mode="json"),
        validated_payload=original_payload.model_dump(mode="json"),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    product = SimpleNamespace(
        id=product_id,
        sku="DF-LPER-Z2CC",
        asin="B0GS3SHBNH",
        title="Seat Cover",
        marketplace_id="A1PA6795UKMFR9",
    )

    db_session = FakeSession()
    db_session.registry[("AplusDraft", draft_id)] = draft
    db_session.registry[("Product", product_id)] = product

    service = AplusService(
        db_session,
        StubAmazonService(),
        OpenAiAplusService(Settings(OPENAI_API_KEY="", OPENAI_MODEL="gpt-4o-mini")),
    )

    response = service.save_draft(draft_id=draft_id, draft_payload=improved_payload)

    assert response.draft_payload.headline == "Sharper shopper outcome headline"
    assert response.optimization_report.overall_score == build_aplus_optimization_report(
        draft_payload=improved_payload
    ).overall_score
    assert response.readiness_report.checked_payload == "draft"
    assert response.status == "draft"
