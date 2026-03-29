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
    def __init__(self) -> None:
        self.registry: dict[tuple[str, object], object] = {}

    def commit(self) -> None:
        return None

    def refresh(self, _: object) -> None:
        return None

    def add(self, _: object) -> None:
        return None

    def flush(self) -> None:
        return None

    def get(self, model: object, key: object) -> object | None:
        model_name = getattr(model, "__name__", str(model))
        return self.registry.get((model_name, key))


class FakeImageProvider:
    def generate_image(self, *, prompt: str, reference_image_paths: list[Path]) -> GeneratedImageResult:
        return GeneratedImageResult(
            content=f"generated::{prompt}::{len(reference_image_paths)}".encode(),
            mime_type="image/png",
            provider_name="test-provider",
        )


class StubAplusImageService(AplusImageService):
    def __init__(self, draft: SimpleNamespace, product: SimpleNamespace, storage_service: MediaStorageService) -> None:
        session = FakeSession()
        super().__init__(session, FakeImageProvider(), storage_service)
        self._draft = draft
        self._product = product
        self.created_asset_count = 0
        self.fake_session = session

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
        self.created_asset_count += 1
        return SimpleNamespace(
            id=uuid4(),
            public_url="/media/aplus-assets/generated-test.png",
        )

    @staticmethod
    def _asset_model():
        return type("AplusAsset", (), {})


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
        reordered_target = next(
            module for module in reordered.modules if module.module_id == "feature-0001"
        )
        reordered_target.image_status = "queued"
        reordered_target.image_request_fingerprint = service._build_request_fingerprint(
            draft_id=draft.id,
            module_id="feature-0001",
            prompt=reordered_target.image_prompt or reordered_target.image_brief,
            reference_asset_ids=reordered_target.reference_asset_ids,
        )
        draft.draft_payload = reordered.model_dump(mode="json")

        service.process_generation(
            draft_id=draft.id,
            module_id="feature-0001",
            request_fingerprint=reordered_target.image_request_fingerprint,
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
            request_fingerprint="stale-fingerprint",
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
            request_fingerprint="stale-fingerprint",
            requested_by_id=None,
        )

    updated = AplusDraftPayload.model_validate(draft.draft_payload)
    assert all(module.image_status == "idle" for module in updated.modules)
    assert all(module.generated_image_url is None for module in updated.modules)


def test_queue_image_generation_rejects_duplicate_inflight_request() -> None:
    payload = build_payload()
    draft, product = build_entities(payload)
    asset_a = uuid4()
    asset_b = uuid4()

    with TemporaryDirectory() as tmpdir:
        service = StubAplusImageService(
            draft,
            product,
            MediaStorageService(root=Path(tmpdir), url_prefix="/media"),
        )
        asset_model = service._asset_model()
        service.fake_session.registry[(asset_model.__name__, asset_a)] = SimpleNamespace(
            id=asset_a,
            product_id=product.id,
        )
        service.fake_session.registry[(asset_model.__name__, asset_b)] = SimpleNamespace(
            id=asset_b,
            product_id=product.id,
        )

        requested_by = SimpleNamespace(id=uuid4())
        _, should_enqueue = service.queue_image_generation(
            draft_id=draft.id,
            module_id="feature-0001",
            image_prompt="Focused prompt",
            overlay_text=None,
            reference_asset_ids=[str(asset_a), str(asset_b)],
            requested_by=requested_by,
        )

        assert should_enqueue is True

        try:
            service.queue_image_generation(
                draft_id=draft.id,
                module_id="feature-0001",
                image_prompt="Focused prompt",
                overlay_text=None,
                reference_asset_ids=[str(asset_a), str(asset_b)],
                requested_by=requested_by,
            )
        except ValueError as exc:
            assert str(exc) == "Image generation is already in progress for this module."
        else:
            raise AssertionError("Expected duplicate in-flight image request to be rejected.")


def test_process_generation_is_idempotent_for_redelivery() -> None:
    payload = build_payload()
    draft, product = build_entities(payload)
    asset_id = uuid4()

    with TemporaryDirectory() as tmpdir:
        service = StubAplusImageService(
            draft,
            product,
            MediaStorageService(root=Path(tmpdir), url_prefix="/media"),
        )
        asset_model = service._asset_model()
        service.fake_session.registry[(asset_model.__name__, asset_id)] = SimpleNamespace(
            id=asset_id,
            product_id=product.id,
        )

        requested_by = SimpleNamespace(id=uuid4())
        _, should_enqueue = service.queue_image_generation(
            draft_id=draft.id,
            module_id="feature-0001",
            image_prompt="Focused prompt",
            overlay_text=None,
            reference_asset_ids=[str(asset_id)],
            requested_by=requested_by,
        )
        assert should_enqueue is True

        queued_payload = AplusDraftPayload.model_validate(draft.draft_payload)
        fingerprint = next(
            module.image_request_fingerprint
            for module in queued_payload.modules
            if module.module_id == "feature-0001"
        )

        service.process_generation(
            draft_id=draft.id,
            module_id="feature-0001",
            request_fingerprint=fingerprint or "",
            requested_by_id=None,
        )
        service.process_generation(
            draft_id=draft.id,
            module_id="feature-0001",
            request_fingerprint=fingerprint or "",
            requested_by_id=None,
        )

        updated = AplusDraftPayload.model_validate(draft.draft_payload)
        target = next(module for module in updated.modules if module.module_id == "feature-0001")

        assert target.image_status == "completed"
        assert service.created_asset_count == 1


def test_mark_enqueue_failed_updates_queued_module() -> None:
    payload = build_payload()
    draft, product = build_entities(payload)

    with TemporaryDirectory() as tmpdir:
        service = StubAplusImageService(
            draft,
            product,
            MediaStorageService(root=Path(tmpdir), url_prefix="/media"),
        )

        requested_by = SimpleNamespace(id=uuid4())
        service.queue_image_generation(
            draft_id=draft.id,
            module_id="feature-0001",
            image_prompt="Focused prompt",
            overlay_text=None,
            reference_asset_ids=[],
            requested_by=requested_by,
        )
        queued_payload = AplusDraftPayload.model_validate(draft.draft_payload)
        fingerprint = next(
            module.image_request_fingerprint
            for module in queued_payload.modules
            if module.module_id == "feature-0001"
        )

        service.mark_enqueue_failed(
            draft_id=draft.id,
            module_id="feature-0001",
            request_fingerprint=fingerprint or "",
            error_message="Broker unavailable",
        )

    updated = AplusDraftPayload.model_validate(draft.draft_payload)
    target = next(module for module in updated.modules if module.module_id == "feature-0001")

    assert target.image_status == "failed"
    assert target.image_error_message == "Broker unavailable"


def test_queue_image_generation_rejects_invalid_reference_asset() -> None:
    payload = build_payload()
    draft, product = build_entities(payload)

    with TemporaryDirectory() as tmpdir:
        service = StubAplusImageService(
            draft,
            product,
            MediaStorageService(root=Path(tmpdir), url_prefix="/media"),
        )

        requested_by = SimpleNamespace(id=uuid4())

        try:
            service.queue_image_generation(
                draft_id=draft.id,
                module_id="feature-0001",
                image_prompt="Focused prompt",
                overlay_text=None,
                reference_asset_ids=["not-a-uuid"],
                requested_by=requested_by,
            )
        except ValueError as exc:
            assert str(exc) == "Invalid reference asset id."
        else:
            raise AssertionError("Expected invalid reference asset id to be rejected.")


def test_queue_image_generation_rejects_cross_product_reference_asset() -> None:
    payload = build_payload()
    draft, product = build_entities(payload)

    with TemporaryDirectory() as tmpdir:
        service = StubAplusImageService(
            draft,
            product,
            MediaStorageService(root=Path(tmpdir), url_prefix="/media"),
        )

        foreign_asset_id = uuid4()
        service.fake_session.registry[("AplusAsset", foreign_asset_id)] = SimpleNamespace(
            id=foreign_asset_id,
            product_id=uuid4(),
        )
        requested_by = SimpleNamespace(id=uuid4())

        try:
            service.queue_image_generation(
                draft_id=draft.id,
                module_id="feature-0001",
                image_prompt="Focused prompt",
                overlay_text=None,
                reference_asset_ids=[str(foreign_asset_id)],
                requested_by=requested_by,
            )
        except ValueError as exc:
            assert str(exc) == "Reference asset does not belong to this product."
        else:
            raise AssertionError("Expected cross-product reference asset to be rejected.")
