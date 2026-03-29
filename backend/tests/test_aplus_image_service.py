from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from uuid import uuid4

from app.schemas.aplus import AplusDraftPayload
from app.services.ai.image_provider import GeneratedImageResult
from app.services.aplus_image_service import AplusImageService
from app.services.media_storage import MediaStorageService


class FakeSession:
    def commit(self) -> None:
        return None

    def refresh(self, _: object) -> None:
        return None

    def add(self, _: object) -> None:
        return None

    def flush(self) -> None:
        return None


class FakeImageProvider:
    def generate_image(self, *, prompt: str, reference_image_paths: list[Path]) -> GeneratedImageResult:
        return GeneratedImageResult(
            content=f"generated::{prompt}::{len(reference_image_paths)}".encode(),
            mime_type="image/png",
            provider_name="test-provider",
        )


class StubAplusImageService(AplusImageService):
    def __init__(self, draft: SimpleNamespace, product: SimpleNamespace, storage_service: MediaStorageService) -> None:
        super().__init__(FakeSession(), FakeImageProvider(), storage_service)
        self._draft = draft
        self._product = product

    def _serializer(self):  # type: ignore[override]
        return SimpleNamespace(_serialize_draft=lambda **_: {"status": "queued"})

    def _get_draft(self, draft_id):  # type: ignore[override]
        assert draft_id == self._draft.id
        return self._draft

    def _get_product(self, product_id):  # type: ignore[override]
        assert product_id == self._product.id
        return self._product

    def _resolve_reference_paths(self, asset_ids: list[str]) -> list[Path]:
        return []

    def _create_generated_asset(self, **kwargs):  # type: ignore[override]
        return SimpleNamespace(
            id=uuid4(),
            public_url="/media/aplus-assets/generated-test.png",
        )


def build_payload() -> AplusDraftPayload:
    return AplusDraftPayload.model_validate(
        {
            "headline": "Comfort that works",
            "subheadline": "Clear support for daily routines and buying confidence.",
            "brand_story": (
                "This draft explains the product angle, why the construction helps in daily use, "
                "and how it stands apart from generic alternatives."
            ),
            "key_features": [
                "Explains the practical material benefit",
                "Clarifies the fit for repeat use",
                "Shows why the product is easier to trust",
            ],
            "modules": [
                {
                    "module_id": "hero-0001",
                    "module_type": "hero",
                    "headline": "Lead benefit",
                    "body": "Explain the primary outcome and why it matters in normal use.",
                    "bullets": ["Primary benefit", "Usage clarity"],
                    "image_brief": "Show the product in a realistic daily-use setting.",
                },
                {
                    "module_id": "feature-0001",
                    "module_type": "feature",
                    "headline": "Feature depth",
                    "body": "Tie the construction detail to a practical customer outcome.",
                    "bullets": ["Specific detail", "Customer benefit"],
                    "image_brief": "Use a close-up detail shot of the product feature.",
                },
                {
                    "module_id": "comparison-0001",
                    "module_type": "comparison",
                    "headline": "Compared with generic",
                    "body": "Show how this product is more precise than generic alternatives.",
                    "bullets": ["Fit | Tailored support | Basic support"],
                    "image_brief": "Show the product beside a generic alternative setup.",
                },
            ],
            "compliance_notes": [
                "Verify the factual claims before publishing.",
                "Review any creative assumptions before launch.",
            ],
        }
    )


def build_entities(payload: AplusDraftPayload) -> tuple[SimpleNamespace, SimpleNamespace]:
    product = SimpleNamespace(
        id=uuid4(),
        sku="SKU-123",
        asin="B0TEST123",
        title="Test Product",
        brand="Brand",
        marketplace_id="A1PA6795UKMFR9",
        source="amazon_listing",
        low_stock_threshold=10,
        is_active=True,
    )
    draft = SimpleNamespace(
        id=uuid4(),
        product_id=product.id,
        status="draft",
        brand_tone=None,
        positioning=None,
        source_language="en-GB",
        target_language="en-GB",
        auto_translate=False,
        draft_payload=payload.model_dump(mode="json"),
        validated_payload=None,
    )
    return draft, product


def test_aplus_payload_backfills_missing_module_ids() -> None:
    payload = AplusDraftPayload.model_validate(
        {
            "headline": "Comfort that works",
            "subheadline": "Clear support for daily routines and buying confidence.",
            "brand_story": (
                "This draft explains the product angle, why the construction helps in daily use, "
                "and how it stands apart from generic alternatives."
            ),
            "key_features": [
                "Explains the practical material benefit",
                "Clarifies the fit for repeat use",
                "Shows why the product is easier to trust",
            ],
            "modules": [
                {
                    "module_type": "hero",
                    "headline": "Lead benefit",
                    "body": "Explain the primary outcome and why it matters in normal use.",
                    "bullets": ["Primary benefit", "Usage clarity"],
                    "image_brief": "Show the product in a realistic daily-use setting.",
                },
                {
            "module_id": "duplicate-id-0001",
                    "module_type": "feature",
                    "headline": "Feature depth",
                    "body": "Tie the construction detail to a practical customer outcome.",
                    "bullets": ["Specific detail", "Customer benefit"],
                    "image_brief": "Use a close-up detail shot of the product feature.",
                },
                {
                    "module_id": "duplicate-id-0001",
                    "module_type": "comparison",
                    "headline": "Compared with generic",
                    "body": "Show how this product is more precise than generic alternatives.",
                    "bullets": ["Fit | Tailored support | Basic support"],
                    "image_brief": "Show the product beside a generic alternative setup.",
                },
            ],
            "compliance_notes": [
                "Verify the factual claims before publishing.",
                "Review any creative assumptions before launch.",
            ],
        }
    )

    module_ids = [module.module_id for module in payload.modules]

    assert all(module_ids)
    assert len(set(module_ids)) == len(module_ids)


def test_process_generation_updates_same_module_after_reorder() -> None:
    payload = build_payload()
    draft, product = build_entities(payload)

    with TemporaryDirectory() as tmpdir:
        service = StubAplusImageService(
            draft,
            product,
            MediaStorageService(root=Path(tmpdir), url_prefix="/media"),
        )

        reordered = AplusDraftPayload.model_validate(draft.draft_payload)
        reordered.modules = [reordered.modules[2], reordered.modules[0], reordered.modules[1]]
        draft.draft_payload = reordered.model_dump(mode="json")

        service.process_generation(
            draft_id=draft.id,
            module_id="feature-0001",
            requested_by_id=None,
        )

    updated = AplusDraftPayload.model_validate(draft.draft_payload)
    target = next(module for module in updated.modules if module.module_id == "feature-0001")
    untouched = next(module for module in updated.modules if module.module_id == "comparison-0001")

    assert target.image_status == "completed"
    assert target.generated_image_url is not None
    assert target.selected_asset_id is not None
    assert untouched.image_status == "idle"


def test_process_generation_noops_when_target_module_was_removed() -> None:
    payload = build_payload()
    draft, product = build_entities(payload)

    with TemporaryDirectory() as tmpdir:
        service = StubAplusImageService(
            draft,
            product,
            MediaStorageService(root=Path(tmpdir), url_prefix="/media"),
        )

        removed = AplusDraftPayload.model_validate(draft.draft_payload)
        removed.modules = [
            module for module in removed.modules if module.module_id != "feature-0001"
        ]
        removed.modules.append(
            removed.modules[0].model_copy(
                update={
                    "module_id": "replacement-0001",
                    "module_type": "feature",
                    "headline": "Replacement module",
                }
            )
        )
        draft.draft_payload = removed.model_dump(mode="json")

        service.process_generation(
            draft_id=draft.id,
            module_id="feature-0001",
            requested_by_id=None,
        )

    updated = AplusDraftPayload.model_validate(draft.draft_payload)
    assert all(module.image_status == "idle" for module in updated.modules)


def test_stale_job_targeting_does_not_touch_other_modules() -> None:
    payload = build_payload()
    draft, product = build_entities(payload)

    with TemporaryDirectory() as tmpdir:
        service = StubAplusImageService(
            draft,
            product,
            MediaStorageService(root=Path(tmpdir), url_prefix="/media"),
        )

        service.process_generation(
            draft_id=draft.id,
            module_id="missing-module",
            requested_by_id=None,
        )

    updated = AplusDraftPayload.model_validate(draft.draft_payload)
    assert all(module.image_status == "idle" for module in updated.modules)
    assert all(module.generated_image_url is None for module in updated.modules)
