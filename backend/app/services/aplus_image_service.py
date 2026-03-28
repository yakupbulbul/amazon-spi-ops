from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.entities import AplusAsset, AplusDraft, Product, User
from app.schemas.aplus import AplusDraftPayload, AplusDraftResponse
from app.services.ai.image_provider import GeneratedImageResult, ImageProvider
from app.services.aplus_service import AplusService
from app.services.media_storage import MediaStorageService


class AplusImageService:
    def __init__(
        self,
        db_session: Session,
        image_provider: ImageProvider,
        storage_service: MediaStorageService,
    ) -> None:
        self.db_session = db_session
        self.image_provider = image_provider
        self.storage_service = storage_service

    def queue_image_generation(
        self,
        *,
        draft_id: UUID,
        module_index: int,
        image_prompt: str | None,
        overlay_text: str | None,
        reference_asset_ids: list[str],
        requested_by: User,
    ) -> AplusDraftResponse:
        draft = self._get_draft(draft_id)
        product = self._get_product(draft.product_id)
        payload = self._load_active_payload(draft)
        self._validate_module_index(payload=payload, module_index=module_index)
        module = payload.modules[module_index]
        module.image_mode = "generated"
        module.image_prompt = image_prompt or self._build_default_prompt(
            product=product,
            draft=draft,
            module_index=module_index,
            draft_payload=payload,
        )
        module.overlay_text = overlay_text
        module.reference_asset_ids = reference_asset_ids[:8]
        module.image_status = "queued"
        module.image_error_message = None
        module.generated_image_url = None
        module.selected_asset_id = None
        self._persist_payload(draft=draft, payload=payload)
        self.db_session.commit()
        self.db_session.refresh(draft)
        return self._serializer()._serialize_draft(draft=draft, product=product)

    def process_generation(self, *, draft_id: UUID, module_index: int, requested_by_id: UUID | None) -> None:
        draft = self._get_draft(draft_id)
        product = self._get_product(draft.product_id)
        payload = self._load_active_payload(draft)
        self._validate_module_index(payload=payload, module_index=module_index)
        module = payload.modules[module_index]
        module.image_status = "generating"
        module.image_error_message = None
        self._persist_payload(draft=draft, payload=payload)
        self.db_session.commit()

        try:
            reference_paths = self._resolve_reference_paths(module.reference_asset_ids)
            result = self.image_provider.generate_image(
                prompt=module.image_prompt or self._build_default_prompt(
                    product=product,
                    draft=draft,
                    module_index=module_index,
                    draft_payload=payload,
                ),
                reference_image_paths=reference_paths,
            )
            asset = self._create_generated_asset(
                draft=draft,
                product=product,
                module=module,
                requested_by_id=requested_by_id,
                result=result,
                reference_asset_ids=module.reference_asset_ids,
            )

            payload = self._load_active_payload(draft)
            completed_module = payload.modules[module_index]
            completed_module.image_mode = "generated"
            completed_module.generated_image_url = asset.public_url
            completed_module.selected_asset_id = str(asset.id)
            completed_module.image_status = "completed"
            completed_module.image_error_message = None
            self._persist_payload(draft=draft, payload=payload)
            self.db_session.commit()
        except Exception as exc:
            payload = self._load_active_payload(draft)
            failed_module = payload.modules[module_index]
            failed_module.image_status = "failed"
            failed_module.image_error_message = str(exc)[:1024]
            self._persist_payload(draft=draft, payload=payload)
            self.db_session.commit()

    def _resolve_reference_paths(self, asset_ids: list[str]) -> list[Path]:
        paths: list[Path] = []
        for asset_id in asset_ids[:4]:
            asset = self.db_session.get(AplusAsset, UUID(asset_id))
            if asset is None:
                continue
            paths.append(self.storage_service.resolve_public_url(asset.public_url))
        return [path for path in paths if path.exists()]

    def _create_generated_asset(
        self,
        *,
        draft: AplusDraft,
        product: Product,
        module,
        requested_by_id: UUID | None,
        result: GeneratedImageResult,
        reference_asset_ids: list[str],
    ) -> AplusAsset:
        suffix = ".png" if result.mime_type == "image/png" else ".jpg"
        _, public_url = self.storage_service.store_bytes(
            subdirectory="aplus-assets",
            suffix=suffix,
            content=result.content,
        )
        asset = AplusAsset(
            product_id=product.id,
            created_by_id=requested_by_id,
            asset_scope="generated",
            label=f"{product.sku} · {module.headline}",
            file_name=f"{product.sku}-{module.headline[:40].strip().replace(' ', '-').lower()}{suffix}",
            mime_type=result.mime_type,
            file_size_bytes=len(result.content),
            public_url=public_url,
            asset_metadata={
                "draft_id": str(draft.id),
                "module_type": module.module_type,
                "provider": result.provider_name,
                "reference_asset_ids": reference_asset_ids,
            },
            created_at=self._now(),
        )
        self.db_session.add(asset)
        self.db_session.flush()
        return asset

    def _build_default_prompt(
        self,
        *,
        product: Product,
        draft: AplusDraft,
        module_index: int,
        draft_payload: AplusDraftPayload,
    ) -> str:
        module = draft_payload.modules[module_index]
        tone = draft.brand_tone or "balanced and product-led"
        positioning = draft.positioning or "marketplace shoppers"
        overlay_instruction = (
            f' Include subtle room for overlay text: "{module.overlay_text}".'
            if module.overlay_text
            else ""
        )
        return (
            f"Create an Amazon A+ image for a {module.module_type} module featuring {product.title} by "
            f"{product.brand or 'the brand'}. Match a {tone} tone for {positioning}. "
            f"Use this creative brief: {module.image_brief}. Support this headline: {module.headline}. "
            f"Keep the image realistic, product-faithful, premium, and suitable for marketplace composition."
            f"{overlay_instruction} Avoid misleading product details or stock-photo generic scenes."
        )

    def _persist_payload(self, *, draft: AplusDraft, payload: AplusDraftPayload) -> None:
        dumped_payload = payload.model_dump(mode="json")
        draft.draft_payload = dumped_payload
        if draft.validated_payload is not None:
            draft.validated_payload = dumped_payload

    @staticmethod
    def _validate_module_index(*, payload: AplusDraftPayload, module_index: int) -> None:
        if module_index < 0 or module_index >= len(payload.modules):
            raise ValueError("A+ module not found.")

    @staticmethod
    def _load_active_payload(draft: AplusDraft) -> AplusDraftPayload:
        return AplusDraftPayload.model_validate(draft.validated_payload or draft.draft_payload)

    def _serializer(self) -> AplusService:
        return AplusService(self.db_session, None, None)  # type: ignore[arg-type]

    def _get_draft(self, draft_id: UUID) -> AplusDraft:
        draft = self.db_session.get(AplusDraft, draft_id)
        if draft is None:
            raise ValueError("A+ draft not found.")
        return draft

    def _get_product(self, product_id: UUID) -> Product:
        product = self.db_session.get(Product, product_id)
        if product is None:
            raise ValueError("Product not found.")
        return product

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)
