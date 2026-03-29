from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import DraftStatus, JobStatus
from app.schemas.aplus import (
    AplusDraftListResponse,
    AplusDraftPayload,
    AplusDraftResponse,
    AplusModulePayload,
    AplusPublishResponse,
    SupportedAplusLanguage,
)
from app.services.ai.openai_service import OpenAiAplusService
from app.services.aplus_optimization import build_aplus_optimization_report
from app.services.aplus_readiness import build_aplus_readiness_report
from app.services.amazon.service import AmazonSpApiService
from app.services.media_storage import MediaStorageService
from app.services.notification_service import NotificationService
from app.services.product_service import ProductService

if TYPE_CHECKING:
    from app.models.entities import AplusAsset, AplusDraft, Product, User


class AplusService:
    def __init__(
        self,
        db_session: Session,
        amazon_service: AmazonSpApiService,
        openai_service: OpenAiAplusService,
        media_storage_service: MediaStorageService | None = None,
    ) -> None:
        self.db_session = db_session
        self.amazon_service = amazon_service
        self.openai_service = openai_service
        self.media_storage_service = media_storage_service or MediaStorageService()

    def list_drafts(self) -> AplusDraftListResponse:
        from app.models.entities import AplusDraft, Product

        drafts = self.db_session.execute(
            select(AplusDraft, Product)
            .join(Product, Product.id == AplusDraft.product_id)
            .order_by(AplusDraft.updated_at.desc())
        ).all()
        return AplusDraftListResponse(
            items=[self._serialize_draft(draft=draft, product=product) for draft, product in drafts]
        )

    def generate_draft(
        self,
        *,
        product_id: UUID,
        brand_tone: str | None,
        positioning: str | None,
        source_language: SupportedAplusLanguage,
        target_language: SupportedAplusLanguage | None,
        auto_translate: bool,
        requested_by: User,
    ) -> AplusDraftResponse:
        product = self._get_product(product_id)
        effective_target_language = target_language or source_language
        product_context = ProductService(self.db_session, self.amazon_service).list_products()
        product_summary = next(
            (item for item in product_context.items if item.id == str(product.id)),
            None,
        )
        draft_payload = self.openai_service.generate_aplus_draft(
            product_context={
                "title": product.title,
                "brand": product.brand,
                "sku": product.sku,
                "asin": product.asin,
                "marketplace_id": product.marketplace_id,
                "price_amount": str(product.price_amount) if product.price_amount is not None else None,
                "price_currency": product.price_currency,
                "inventory": product_summary.inventory.model_dump() if product_summary and product_summary.inventory else None,
            },
            brand_tone=brand_tone,
            positioning=positioning,
            source_language=source_language,
        )
        if auto_translate:
            draft_payload = self.openai_service.translate_aplus_draft(
                draft_payload=draft_payload,
                source_language=source_language,
                target_language=effective_target_language,
            )

        from app.models.entities import AplusDraft

        draft = AplusDraft(
            product_id=product.id,
            status=DraftStatus.DRAFT.value,
            brand_tone=brand_tone,
            positioning=positioning,
            source_language=source_language,
            target_language=effective_target_language,
            auto_translate=auto_translate,
            draft_payload=draft_payload.model_dump(mode="json"),
            validated_payload=None,
            created_by_id=requested_by.id,
        )
        self.db_session.add(draft)
        self.db_session.commit()
        self.db_session.refresh(draft)
        return self._serialize_draft(draft=draft, product=product)

    def validate_draft(self, *, draft_id: UUID, draft_payload: AplusDraftPayload) -> AplusDraftResponse:
        draft = self._get_draft(draft_id)
        product = self._get_product(draft.product_id)
        readiness_report = build_aplus_readiness_report(
            draft_payload=draft_payload,
            checked_payload="validated",
        )
        draft.validated_payload = draft_payload.model_dump(mode="json")
        draft.status = (
            DraftStatus.READY_TO_PUBLISH.value
            if readiness_report.is_publish_ready
            else DraftStatus.VALIDATED.value
        )
        self.db_session.commit()
        self.db_session.refresh(draft)
        return self._serialize_draft(draft=draft, product=product)

    def publish_draft(self, *, draft_id: UUID) -> AplusPublishResponse:
        draft = self._get_draft(draft_id)
        product = self._get_product(draft.product_id)
        notification_service = NotificationService(self.db_session)
        timestamp = self._now()

        try:
            if draft.validated_payload is None:
                raise ValueError("Validate the draft before preparing the publish payload.")

            validated_payload = AplusDraftPayload.model_validate(draft.validated_payload)
            readiness_report = build_aplus_readiness_report(
                draft_payload=validated_payload,
                checked_payload="validated",
            )
            if not readiness_report.is_publish_ready:
                error_summary = ", ".join(
                    issue.message for issue in readiness_report.blocking_errors[:3]
                )
                raise ValueError(
                    "Draft is not publish-ready. Resolve blocking issues first: "
                    f"{error_summary}"
                )

            prepared_payload = self._build_amazon_payload(
                product=product,
                draft_payload=validated_payload,
                target_language=draft.target_language,
            )

            from app.models.entities import AplusPublishJob

            publish_job = AplusPublishJob(
                draft_id=draft.id,
                status=JobStatus.SUCCEEDED.value,
                external_submission_id="preview-only",
                submitted_at=timestamp,
                completed_at=timestamp,
                created_at=timestamp,
            )
            self.db_session.add(publish_job)
            draft.status = DraftStatus.READY_TO_PUBLISH.value
            draft.validated_payload = validated_payload.model_dump(mode="json")
            notification = notification_service.queue_event_notification(
                event_type="aplus_publish",
                source="aplus_studio",
                event_status=JobStatus.SUCCEEDED.value,
                event_payload={
                    "sku": product.sku,
                    "asin": product.asin,
                    "draft_id": str(draft.id),
                    "marketplace_id": product.marketplace_id,
                },
                notification_type="aplus_publish_success",
                message_preview=f"A+ publish payload prepared for {product.sku}.",
                occurred_at=timestamp,
            )
            self.db_session.commit()
            notification_service.dispatch_notification(notification.id)
            self.db_session.refresh(draft)
            self.db_session.refresh(publish_job)

            return AplusPublishResponse(
                draft=self._serialize_draft(draft=draft, product=product),
                publish_job_id=str(publish_job.id),
                status=publish_job.status,
                message=(
                    "Prepared an Amazon-compatible A+ payload. "
                    "Live submission remains account-dependent and can be added to the publish adapter."
                ),
                prepared_payload=prepared_payload,
            )
        except Exception as exc:
            from app.models.entities import AplusPublishJob

            publish_job = AplusPublishJob(
                draft_id=draft.id,
                status=JobStatus.FAILED.value,
                error_message=str(exc)[:1024],
                submitted_at=timestamp,
                completed_at=timestamp,
                created_at=timestamp,
            )
            self.db_session.add(publish_job)
            notification = notification_service.queue_event_notification(
                event_type="aplus_publish",
                source="aplus_studio",
                event_status=JobStatus.FAILED.value,
                event_payload={
                    "sku": product.sku,
                    "asin": product.asin,
                    "draft_id": str(draft.id),
                    "error": str(exc),
                },
                notification_type="aplus_publish_failure",
                message_preview=f"A+ publish preparation failed for {product.sku}.",
                occurred_at=timestamp,
            )
            self.db_session.commit()
            notification_service.dispatch_notification(notification.id)
            raise

    def _build_amazon_payload(
        self,
        *,
        product: Product,
        draft_payload: AplusDraftPayload,
        target_language: str,
    ) -> dict[str, object]:
        locale = self._marketplace_locale(product.marketplace_id)
        draft_locale = target_language or locale
        content_modules = self._build_publishable_modules(
            product=product,
            draft_payload=draft_payload,
        )

        amazon_content = {
            "contentDocument": {
                "name": f"{product.title} A+ draft",
                "locale": draft_locale,
                "contentSubType": "EMC",
                "headline": draft_payload.headline,
                "subheadline": draft_payload.subheadline,
                "brandStory": draft_payload.brand_story,
                "keyFeatures": draft_payload.key_features,
                "contentModuleList": content_modules,
                "complianceNotes": draft_payload.compliance_notes,
            }
        }
        return self.amazon_service.live_adapter.prepare_aplus_content_payload(
            asin=product.asin,
            draft_content=amazon_content,
            marketplace_id=product.marketplace_id,
        )

    @staticmethod
    def _amazon_module_type(module_type: str, *, has_image: bool) -> str:
        mapping = {
            "hero": "STANDARD_HEADER_IMAGE_TEXT" if has_image else "STANDARD_TEXT",
            "feature": "STANDARD_SINGLE_IMAGE_HIGHLIGHTS" if has_image else "STANDARD_TEXT",
            "comparison": "STANDARD_COMPARISON_TABLE",
            "faq": "STANDARD_TEXT",
        }
        return mapping.get(
            module_type,
            "STANDARD_SINGLE_IMAGE_HIGHLIGHTS" if has_image else "STANDARD_TEXT",
        )

    @staticmethod
    def _marketplace_locale(marketplace_id: str) -> str:
        mapping = {
            "A1PA6795UKMFR9": "de-DE",
            "ATVPDKIKX0DER": "en-US",
            "A1F83G8C2ARO7P": "en-GB",
        }
        return mapping.get(marketplace_id, "en-US")

    def _build_publishable_modules(
        self,
        *,
        product: Product,
        draft_payload: AplusDraftPayload,
    ) -> list[dict[str, object]]:
        content_modules: list[dict[str, object]] = []
        errors: list[str] = []

        for index, module in enumerate(draft_payload.modules, start=1):
            try:
                content_modules.append(
                    self._build_publishable_module(
                        product=product,
                        module_index=index,
                        module=module,
                    )
                )
            except ValueError as exc:
                errors.append(f"Module {index} ({module.module_type}): {exc}")

        if errors:
            raise ValueError(
                "Draft contains non-publishable module content. " + " ".join(errors[:6])
            )

        return content_modules

    def _build_publishable_module(
        self,
        *,
        product: Product,
        module_index: int,
        module: AplusModulePayload,
    ) -> dict[str, object]:
        resolved_image_url = self._resolve_module_image_url(
            product=product,
            module_index=module_index,
            module=module,
        )
        has_image = resolved_image_url is not None
        publishable_module: dict[str, object] = {
            "contentModuleType": self._amazon_module_type(module.module_type, has_image=has_image),
            "headline": module.headline,
            "body": module.body,
            "bullets": module.bullets,
        }

        if module.module_type == "comparison":
            publishable_module["comparisonRows"] = [
                self._parse_comparison_row(row) for row in module.bullets
            ]

        if has_image:
            publishable_module["image"] = {
                "assetUrl": resolved_image_url,
                "altText": module.image_brief,
            }
            if module.overlay_text and self._module_supports_overlay(module.module_type):
                publishable_module["overlayText"] = module.overlay_text
        else:
            publishable_module["imageBrief"] = module.image_brief

        return publishable_module

    def _resolve_module_image_url(
        self,
        *,
        product: Product,
        module_index: int,
        module: AplusModulePayload,
    ) -> str | None:
        supports_image = self._module_supports_image(module.module_type)

        if not supports_image:
            if module.image_mode != "none":
                raise ValueError("selected image mode is not supported for this module type.")
            if module.overlay_text:
                raise ValueError("overlay text is not publishable for this module type.")
            return None

        if module.image_mode == "none":
            if module.overlay_text:
                raise ValueError("overlay text requires a publishable image selection.")
            return None

        if module.image_mode == "generated":
            if not module.generated_image_url:
                raise ValueError("generated image is selected but no generated asset is available.")
            self._ensure_publishable_media_url(
                module.generated_image_url,
                field_label=f"Module {module_index} generated image",
            )
            return module.generated_image_url

        if module.image_mode == "uploaded":
            if not module.uploaded_image_url:
                raise ValueError("uploaded image is selected but no uploaded asset is available.")
            self._ensure_publishable_media_url(
                module.uploaded_image_url,
                field_label=f"Module {module_index} uploaded image",
            )
            return module.uploaded_image_url

        if module.image_mode == "existing_asset":
            if not module.selected_asset_id:
                raise ValueError("existing asset mode requires a selected asset.")
            asset = self._get_publishable_asset(
                product=product,
                asset_id=module.selected_asset_id,
                field_label=f"Module {module_index} existing asset",
            )
            self._ensure_publishable_media_url(
                asset.public_url,
                field_label=f"Module {module_index} existing asset",
            )
            return asset.public_url

        raise ValueError("unsupported image mode.")

    def _get_publishable_asset(
        self,
        *,
        product: Product,
        asset_id: str,
        field_label: str,
    ) -> AplusAsset:
        from app.models.entities import AplusAsset

        try:
            asset_uuid = UUID(asset_id)
        except ValueError as exc:
            raise ValueError(f"{field_label} has an invalid asset identifier.") from exc

        asset = self.db_session.get(AplusAsset, asset_uuid)
        if asset is None:
            raise ValueError(f"{field_label} could not be found.")
        if asset.product_id is not None and asset.product_id != product.id:
            raise ValueError(f"{field_label} is outside the allowed product scope.")
        return asset

    def _ensure_publishable_media_url(self, public_url: str, *, field_label: str) -> None:
        url_prefix = f"{self.media_storage_service.url_prefix}/"
        if not public_url.startswith(url_prefix):
            raise ValueError(f"{field_label} must resolve to a locally stored media asset.")

        file_path = self.media_storage_service.resolve_public_url(public_url)
        if not file_path.exists():
            raise ValueError(f"{field_label} is missing from storage.")

    @staticmethod
    def _module_supports_image(module_type: str) -> bool:
        return module_type in {"hero", "feature"}

    @staticmethod
    def _module_supports_overlay(module_type: str) -> bool:
        return module_type in {"hero", "feature"}

    @staticmethod
    def _parse_comparison_row(value: str) -> dict[str, str]:
        parts = [part.strip() for part in value.split("|")]
        return {
            "criteria": parts[0] if len(parts) > 0 else "",
            "thisProduct": parts[1] if len(parts) > 1 else "",
            "genericAlternative": parts[2] if len(parts) > 2 else "",
        }

    def _get_draft(self, draft_id: UUID) -> AplusDraft:
        from app.models.entities import AplusDraft

        draft = self.db_session.get(AplusDraft, draft_id)
        if draft is None:
            raise ValueError("A+ draft not found.")
        return draft

    def _get_product(self, product_id: UUID) -> Product:
        from app.models.entities import Product

        product = self.db_session.get(Product, product_id)
        if product is None:
            raise ValueError("Product not found.")
        return product

    def _serialize_draft(self, *, draft: AplusDraft, product: Product) -> AplusDraftResponse:
        checked_payload = "validated" if draft.validated_payload is not None else "draft"
        active_payload = AplusDraftPayload.model_validate(
            draft.validated_payload or draft.draft_payload
        )
        return AplusDraftResponse(
            id=str(draft.id),
            product_id=str(product.id),
            product_sku=product.sku,
            product_asin=product.asin,
            product_title=product.title,
            marketplace_id=product.marketplace_id,
            status=draft.status,
            brand_tone=draft.brand_tone,
            positioning=draft.positioning,
            source_language=draft.source_language,
            target_language=draft.target_language,
            auto_translate=draft.auto_translate,
            draft_payload=AplusDraftPayload.model_validate(draft.draft_payload),
            validated_payload=(
                AplusDraftPayload.model_validate(draft.validated_payload)
                if draft.validated_payload is not None
                else None
            ),
            readiness_report=build_aplus_readiness_report(
                draft_payload=active_payload,
                checked_payload=checked_payload,
            ),
            optimization_report=build_aplus_optimization_report(
                draft_payload=active_payload,
            ),
            created_at=draft.created_at,
            updated_at=draft.updated_at,
        )

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)
