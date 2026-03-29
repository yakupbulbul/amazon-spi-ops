from __future__ import annotations

from base64 import b64encode
from datetime import datetime, timezone
from hashlib import md5
from io import BytesIO
from typing import TYPE_CHECKING
from uuid import UUID

from PIL import Image, UnidentifiedImageError
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.enums import DraftStatus, JobStatus
from app.schemas.aplus import (
    AplusDraftListResponse,
    AplusDraftPayload,
    AplusDraftResponse,
    AplusImproveResponse,
    AplusImprovementChange,
    AplusModulePayload,
    AplusPublishJobResponse,
    AplusPublishResponse,
    SupportedAplusImprovementCategory,
    SupportedAplusLanguage,
)
from app.services.ai.openai_service import OpenAiAplusService
from app.services.aplus_optimization import (
    build_aplus_improvement_issues,
    build_aplus_optimization_report,
)
from app.services.aplus_readiness import build_aplus_readiness_report
from app.services.amazon.aplus_contract import AmazonContractMapper, PreparedAmazonImageAsset
from app.services.amazon.exceptions import AmazonRequestError
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
        self.contract_mapper = AmazonContractMapper()

    def get_latest_publish_job(
        self,
        *,
        draft_id: UUID,
        refresh: bool = True,
    ) -> AplusPublishJobResponse | None:
        draft = self._get_draft(draft_id)
        publish_job = self._get_latest_publish_job_record(draft_id=draft.id)
        if publish_job is None:
            return None

        if refresh and publish_job.external_submission_id and publish_job.status in {"submitted", "in_review"}:
            self._refresh_publish_job_status(draft=draft, publish_job=publish_job)
            self.db_session.commit()
            self.db_session.refresh(publish_job)
            self.db_session.refresh(draft)

        return self._serialize_publish_job(publish_job)

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
        product_context = self._build_product_context(product=product)
        draft_payload = self.openai_service.generate_aplus_draft(
            product_context=product_context,
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

    def improve_draft(
        self,
        *,
        draft_id: UUID,
        draft_payload: AplusDraftPayload,
        category: SupportedAplusImprovementCategory,
    ) -> AplusImproveResponse:
        draft = self._get_draft(draft_id)
        product = self._get_product(draft.product_id)
        product_context = self._build_product_context(product=product)
        issues = build_aplus_improvement_issues(
            draft_payload=draft_payload,
            category=category,
        )
        improved_payload, summary = self.openai_service.improve_aplus_draft(
            draft_payload=draft_payload,
            category=category,
            issues=[issue.message for issue in issues],
            language=draft.target_language,
            product_context=product_context,
        )
        return AplusImproveResponse(
            category=category,
            summary=summary,
            issues=issues,
            improved_payload=improved_payload,
            changes=self._build_improvement_changes(
                original_payload=draft_payload,
                improved_payload=improved_payload,
            ),
        )

    def publish_draft(self, *, draft_id: UUID) -> AplusPublishResponse:
        draft = self._get_draft(draft_id)
        product = self._get_product(draft.product_id)
        notification_service = NotificationService(self.db_session)
        timestamp = self._now()
        publish_job = self._create_publish_job(draft_id=draft.id, created_at=timestamp)
        self.db_session.add(publish_job)
        self.db_session.commit()
        self.db_session.refresh(publish_job)

        try:
            if not settings.aplus_live_publish_enabled:
                raise ValueError(
                    "Live Amazon A+ publish is disabled. Set APLUS_LIVE_PUBLISH_ENABLED=true in the dedicated live test environment before submitting."
                )
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

            prepared_payload = self._publish_to_amazon(
                product=product,
                draft_payload=validated_payload,
                target_language=draft.target_language,
                publish_job=publish_job,
            )
            self._refresh_publish_job_status(draft=draft, publish_job=publish_job)
            notification = notification_service.queue_event_notification(
                event_type="aplus_publish",
                source="aplus_studio",
                event_status=publish_job.status,
                event_payload={
                    "sku": product.sku,
                    "asin": product.asin,
                    "draft_id": str(draft.id),
                    "marketplace_id": product.marketplace_id,
                    "content_reference_key": publish_job.external_submission_id,
                },
                notification_type="aplus_publish_success",
                message_preview=f"A+ content submitted to Amazon for {product.sku}.",
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
                    "Submitted the A+ content document to Amazon using the supported real publish subset."
                ),
                publish_job=self._serialize_publish_job(publish_job),
                prepared_payload=prepared_payload,
            )
        except Exception as exc:
            publish_job.status = "failed"
            publish_job.error_message = str(exc)[:1024]
            publish_job.completed_at = timestamp
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

    def _publish_to_amazon(
        self,
        *,
        product: Product,
        draft_payload: AplusDraftPayload,
        target_language: str,
        publish_job=None,
    ) -> dict[str, object]:
        locale = target_language or self._marketplace_locale(product.marketplace_id)
        prepared_assets = self._prepare_amazon_assets(
            product=product,
            draft_payload=draft_payload,
        )
        if publish_job is not None:
            self._set_publish_job_state(
                publish_job=publish_job,
                status="assets_prepared",
                response_payload={
                    "assetPreparation": {
                        module_id: {
                            "uploadDestinationId": prepared_asset.upload_destination_id,
                            "width": prepared_asset.width_pixels,
                            "height": prepared_asset.height_pixels,
                            "cropWidth": prepared_asset.crop_width_pixels,
                            "cropHeight": prepared_asset.crop_height_pixels,
                            "cropOffsetX": prepared_asset.crop_offset_x_pixels,
                            "cropOffsetY": prepared_asset.crop_offset_y_pixels,
                            "assetId": prepared_asset.asset_id,
                        }
                        for module_id, prepared_asset in prepared_assets.items()
                    }
                },
            )
        content_document_request = self.contract_mapper.map_content_document(
            product_title=product.title,
            locale=locale,
            draft_payload=draft_payload,
            prepared_assets_by_module_id=prepared_assets,
        )
        request_payload = content_document_request.model_dump(mode="json")

        validation_response = self.amazon_service.validate_aplus_content_document(
            marketplace_id=product.marketplace_id,
            asin_set=[product.asin],
            document_request=request_payload,
        )
        validation_errors = validation_response.get("errors") or []
        if validation_errors:
            raise ValueError(
                "Amazon validation rejected the A+ content document: "
                + "; ".join(error.get("message", "Unknown validation error") for error in validation_errors[:5])
            )
        if publish_job is not None:
            self._set_publish_job_state(
                publish_job=publish_job,
                status="validated",
                response_payload={
                    "assetPreparation": publish_job.response_payload.get("assetPreparation", {})
                    if publish_job.response_payload
                    else {},
                    "contentDocumentRequest": request_payload,
                    "validationResponse": validation_response,
                },
            )

        create_response = self.amazon_service.create_aplus_content_document(
            marketplace_id=product.marketplace_id,
            document_request=request_payload,
        )
        content_reference_key = create_response.get("contentReferenceKey")
        if not content_reference_key:
            raise ValueError("Amazon did not return a contentReferenceKey for the new A+ content document.")

        asin_relations_request = self.contract_mapper.build_asin_relations(asin=product.asin)
        asin_relations_response = self.amazon_service.post_aplus_content_document_asin_relations(
            marketplace_id=product.marketplace_id,
            content_reference_key=content_reference_key,
            asin_set=asin_relations_request.asinSet,
        )
        approval_response = self.amazon_service.submit_aplus_content_document_for_approval(
            marketplace_id=product.marketplace_id,
            content_reference_key=content_reference_key,
        )
        if publish_job is not None:
            publish_job.external_submission_id = content_reference_key
            publish_job.submitted_at = self._now()
            self._set_publish_job_state(
                publish_job=publish_job,
                status="submitted",
                response_payload={
                    "assetPreparation": publish_job.response_payload.get("assetPreparation", {})
                    if publish_job.response_payload
                    else {},
                    "contentDocumentRequest": request_payload,
                    "validationResponse": validation_response,
                    "createContentDocumentResponse": create_response,
                    "asinRelationsResponse": asin_relations_response,
                    "approvalSubmissionResponse": approval_response,
                },
            )
        content_status = self.amazon_service.get_aplus_content_document(
            marketplace_id=product.marketplace_id,
            content_reference_key=content_reference_key,
            included_data_set=["METADATA"],
        )

        return {
            "contentReferenceKey": content_reference_key,
            "contentDocumentRequest": request_payload,
            "assetPreparation": {
                module_id: {
                    "uploadDestinationId": prepared_asset.upload_destination_id,
                    "width": prepared_asset.width_pixels,
                    "height": prepared_asset.height_pixels,
                    "cropWidth": prepared_asset.crop_width_pixels,
                    "cropHeight": prepared_asset.crop_height_pixels,
                    "cropOffsetX": prepared_asset.crop_offset_x_pixels,
                    "cropOffsetY": prepared_asset.crop_offset_y_pixels,
                    "assetId": prepared_asset.asset_id,
                }
                for module_id, prepared_asset in prepared_assets.items()
            },
            "validationResponse": validation_response,
            "createContentDocumentResponse": create_response,
            "asinRelationsResponse": asin_relations_response,
            "approvalSubmissionResponse": approval_response,
            "contentRecord": content_status.get("contentRecord"),
        }

    @staticmethod
    def _marketplace_locale(marketplace_id: str) -> str:
        mapping = {
            "A1PA6795UKMFR9": "de-DE",
            "ATVPDKIKX0DER": "en-US",
            "A1F83G8C2ARO7P": "en-GB",
        }
        return mapping.get(marketplace_id, "en-US")

    def _build_product_context(self, *, product: Product) -> dict[str, object]:
        product_context = ProductService(self.db_session, self.amazon_service).list_products()
        product_summary = next(
            (item for item in product_context.items if item.id == str(product.id)),
            None,
        )
        return {
            "title": product.title,
            "brand": product.brand,
            "sku": product.sku,
            "asin": product.asin,
            "marketplace_id": product.marketplace_id,
            "price_amount": str(product.price_amount) if product.price_amount is not None else None,
            "price_currency": product.price_currency,
            "inventory": product_summary.inventory.model_dump()
            if product_summary and product_summary.inventory
            else None,
        }

    def _prepare_amazon_assets(
        self,
        *,
        product: Product,
        draft_payload: AplusDraftPayload,
    ) -> dict[str, PreparedAmazonImageAsset]:
        prepared_assets: dict[str, PreparedAmazonImageAsset] = {}
        for module in draft_payload.modules:
            if module.module_type not in {"hero", "feature"}:
                continue
            asset = self._resolve_module_publish_asset(product=product, module=module)
            prepared_assets[module.module_id] = self._ensure_amazon_asset_ready(
                asset=asset,
                module=module,
                marketplace_id=product.marketplace_id,
            )
        return prepared_assets

    def _resolve_module_publish_asset(
        self,
        *,
        product: Product,
        module: AplusModulePayload,
    ) -> AplusAsset:
        if module.image_mode == "existing_asset":
            if not module.selected_asset_id:
                raise ValueError("Existing asset mode requires a selected asset for Amazon publish.")
            return self._get_publishable_asset(
                product=product,
                asset_id=module.selected_asset_id,
                field_label=f"Module '{module.headline}' existing asset",
            )

        if module.image_mode in {"generated", "uploaded"}:
            if module.selected_asset_id:
                return self._get_publishable_asset(
                    product=product,
                    asset_id=module.selected_asset_id,
                    field_label=f"Module '{module.headline}' selected asset",
                )

            public_url = (
                module.generated_image_url if module.image_mode == "generated" else module.uploaded_image_url
            )
            if not public_url:
                raise ValueError(
                    f"Module '{module.headline}' is missing its selected local image before Amazon publish."
                )
            return self._get_publishable_asset_by_public_url(
                product=product,
                public_url=public_url,
                field_label=f"Module '{module.headline}' local asset",
            )

        raise ValueError(
            f"Module '{module.headline}' requires an image because {module.module_type} is part of the supported Amazon publish subset."
        )

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

    def _get_publishable_asset_by_public_url(
        self,
        *,
        product: Product,
        public_url: str,
        field_label: str,
    ) -> AplusAsset:
        from app.models.entities import AplusAsset

        asset = self.db_session.execute(
            select(AplusAsset)
            .where(AplusAsset.public_url == public_url)
            .where(or_(AplusAsset.product_id == product.id, AplusAsset.product_id.is_(None)))
            .order_by(AplusAsset.created_at.desc())
        ).scalar_one_or_none()
        if asset is None:
            raise ValueError(f"{field_label} could not be resolved to a stored A+ asset.")
        return asset

    def _ensure_amazon_asset_ready(
        self,
        *,
        asset: AplusAsset,
        module: AplusModulePayload,
        marketplace_id: str,
    ) -> PreparedAmazonImageAsset:
        metadata = dict(asset.asset_metadata or {})
        amazon_uploads = dict(metadata.get("amazon_uploads") or {})
        cached_upload = amazon_uploads.get(marketplace_id)
        if isinstance(cached_upload, dict) and cached_upload.get("upload_destination_id"):
            width_pixels = int(cached_upload["width_pixels"])
            height_pixels = int(cached_upload["height_pixels"])
            crop_width_pixels = cached_upload.get("crop_width_pixels")
            crop_height_pixels = cached_upload.get("crop_height_pixels")
            crop_offset_x_pixels = cached_upload.get("crop_offset_x_pixels")
            crop_offset_y_pixels = cached_upload.get("crop_offset_y_pixels")
            if crop_width_pixels is None or crop_height_pixels is None:
                (
                    crop_width_pixels,
                    crop_height_pixels,
                    crop_offset_x_pixels,
                    crop_offset_y_pixels,
                ) = self._build_publish_crop_spec(
                    module=module,
                    width_pixels=width_pixels,
                    height_pixels=height_pixels,
                )
            return PreparedAmazonImageAsset(
                upload_destination_id=str(cached_upload["upload_destination_id"]),
                alt_text=module.image_brief.strip(),
                width_pixels=width_pixels,
                height_pixels=height_pixels,
                crop_width_pixels=int(crop_width_pixels),
                crop_height_pixels=int(crop_height_pixels),
                crop_offset_x_pixels=int(crop_offset_x_pixels or 0),
                crop_offset_y_pixels=int(crop_offset_y_pixels or 0),
                asset_id=str(asset.id),
            )

        file_path = self.media_storage_service.resolve_public_url(asset.public_url)
        if not file_path.exists():
            raise ValueError(f"The selected asset for module '{module.headline}' is missing from local storage.")

        content = file_path.read_bytes()
        if len(content) > settings.aplus_upload_max_bytes:
            raise ValueError(
                f"The selected asset for module '{module.headline}' exceeds the configured Amazon upload size limit."
            )
        if asset.mime_type not in {"image/jpeg", "image/png"}:
            raise ValueError(
                f"Module '{module.headline}' uses {asset.mime_type}, but the supported Amazon publish subset currently accepts only JPEG and PNG images."
            )

        width_pixels, height_pixels = self._read_image_dimensions(
            content=content,
            expected_mime_type=asset.mime_type,
            field_label=f"Module '{module.headline}' image",
        )
        crop_width_pixels, crop_height_pixels, crop_offset_x_pixels, crop_offset_y_pixels = (
            self._build_publish_crop_spec(
                module=module,
                width_pixels=width_pixels,
                height_pixels=height_pixels,
            )
        )
        content_md5 = b64encode(md5(content).digest()).decode("ascii")
        upload_destination = self.amazon_service.create_aplus_upload_destination(
            marketplace_id=marketplace_id,
            content_md5=content_md5,
            content_type=asset.mime_type,
        )
        upload_payload = upload_destination.get("payload") or {}
        upload_destination_id = upload_payload.get("uploadDestinationId")
        upload_url = upload_payload.get("url")
        form_fields = upload_payload.get("headers") or {}
        if not upload_destination_id or not upload_url:
            raise ValueError("Amazon did not return a usable upload destination for the selected image asset.")

        self.amazon_service.upload_asset_to_destination(
            url=str(upload_url),
            form_fields={str(key): str(value) for key, value in form_fields.items()},
            file_name=asset.file_name,
            content=content,
            content_type=asset.mime_type,
        )

        amazon_uploads[marketplace_id] = {
            "upload_destination_id": str(upload_destination_id),
            "width_pixels": width_pixels,
            "height_pixels": height_pixels,
            "crop_width_pixels": crop_width_pixels,
            "crop_height_pixels": crop_height_pixels,
            "crop_offset_x_pixels": crop_offset_x_pixels,
            "crop_offset_y_pixels": crop_offset_y_pixels,
            "mime_type": asset.mime_type,
            "file_size_bytes": len(content),
            "uploaded_at": self._now().isoformat(),
        }
        metadata["amazon_uploads"] = amazon_uploads
        asset.asset_metadata = metadata
        self.db_session.flush()

        return PreparedAmazonImageAsset(
            upload_destination_id=str(upload_destination_id),
            alt_text=module.image_brief.strip(),
            width_pixels=width_pixels,
            height_pixels=height_pixels,
            crop_width_pixels=crop_width_pixels,
            crop_height_pixels=crop_height_pixels,
            crop_offset_x_pixels=crop_offset_x_pixels,
            crop_offset_y_pixels=crop_offset_y_pixels,
            asset_id=str(asset.id),
        )

    @staticmethod
    def _read_image_dimensions(
        *,
        content: bytes,
        expected_mime_type: str,
        field_label: str,
    ) -> tuple[int, int]:
        try:
            with Image.open(BytesIO(content)) as image:
                detected_format = (image.format or "").upper()
                width, height = image.size
        except UnidentifiedImageError as exc:
            raise ValueError(f"{field_label} is not a valid image file.") from exc

        expected_formats = {
            "image/jpeg": {"JPEG"},
            "image/png": {"PNG"},
        }
        if detected_format not in expected_formats.get(expected_mime_type, set()):
            raise ValueError(f"{field_label} does not match the expected MIME type {expected_mime_type}.")
        if width <= 0 or height <= 0:
            raise ValueError(f"{field_label} has invalid image dimensions.")
        return width, height

    @staticmethod
    def _build_publish_crop_spec(
        *,
        module: AplusModulePayload,
        width_pixels: int,
        height_pixels: int,
    ) -> tuple[int, int, int, int]:
        if module.module_type == "hero":
            return AplusService._center_crop_to_ratio(
                width_pixels=width_pixels,
                height_pixels=height_pixels,
                target_width=970,
                target_height=600,
                field_label=f"Module '{module.headline}' hero image",
            )
        if module.module_type == "feature":
            return AplusService._center_crop_to_ratio(
                width_pixels=width_pixels,
                height_pixels=height_pixels,
                target_width=300,
                target_height=300,
                field_label=f"Module '{module.headline}' feature image",
            )
        raise ValueError(f"Module '{module.headline}' is not part of the supported Amazon image subset.")

    @staticmethod
    def _center_crop_to_ratio(
        *,
        width_pixels: int,
        height_pixels: int,
        target_width: int,
        target_height: int,
        field_label: str,
    ) -> tuple[int, int, int, int]:
        if width_pixels < target_width or height_pixels < target_height:
            raise ValueError(
                f"{field_label} must be at least {target_width} x {target_height} pixels for Amazon publish."
            )

        source_ratio = width_pixels / height_pixels
        target_ratio = target_width / target_height
        if source_ratio > target_ratio:
            crop_height = height_pixels
            crop_width = int(round(height_pixels * target_ratio))
        else:
            crop_width = width_pixels
            crop_height = int(round(width_pixels / target_ratio))

        if crop_width < target_width or crop_height < target_height:
            raise ValueError(
                f"{field_label} cannot be cropped safely to the required Amazon aspect ratio."
            )

        offset_x = max((width_pixels - crop_width) // 2, 0)
        offset_y = max((height_pixels - crop_height) // 2, 0)
        return crop_width, crop_height, offset_x, offset_y

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

    def _serialize_publish_job(self, publish_job) -> AplusPublishJobResponse:
        response_payload = publish_job.response_payload or {}
        rejection_reasons = self._extract_publish_job_messages(response_payload, key="errors")
        warnings = self._extract_publish_job_messages(response_payload, key="warnings")
        if publish_job.error_message and publish_job.status == "rejected":
            rejection_reasons = [publish_job.error_message]

        return AplusPublishJobResponse(
            id=str(publish_job.id),
            draft_id=str(publish_job.draft_id),
            status=publish_job.status,
            content_reference_key=publish_job.external_submission_id,
            error_message=publish_job.error_message,
            rejection_reasons=rejection_reasons,
            warnings=warnings,
            submitted_at=publish_job.submitted_at,
            completed_at=publish_job.completed_at,
            created_at=publish_job.created_at,
        )

    @staticmethod
    def _build_improvement_changes(
        *,
        original_payload: AplusDraftPayload,
        improved_payload: AplusDraftPayload,
    ) -> list[AplusImprovementChange]:
        changes: list[AplusImprovementChange] = []

        def add_change(path: str, label: str, before: str, after: str) -> None:
            if before == after:
                return
            changes.append(
                AplusImprovementChange(
                    path=path,
                    label=label,
                    before=before,
                    after=after,
                )
            )

        add_change(
            "headline",
            "Headline",
            original_payload.headline,
            improved_payload.headline,
        )
        add_change(
            "subheadline",
            "Subheadline",
            original_payload.subheadline,
            improved_payload.subheadline,
        )
        add_change(
            "brand_story",
            "Brand story",
            original_payload.brand_story,
            improved_payload.brand_story,
        )

        max_key_features = max(
            len(original_payload.key_features),
            len(improved_payload.key_features),
        )
        for index in range(max_key_features):
            before = original_payload.key_features[index] if index < len(original_payload.key_features) else ""
            after = improved_payload.key_features[index] if index < len(improved_payload.key_features) else ""
            add_change(
                f"key_features[{index}]",
                f"Key feature {index + 1}",
                before,
                after,
            )

        original_modules = {module.module_id: module for module in original_payload.modules}
        for module_index, improved_module in enumerate(improved_payload.modules, start=1):
            original_module = original_modules.get(improved_module.module_id)
            if original_module is None:
                continue
            module_label = f"Module {module_index}"
            add_change(
                f"modules.{improved_module.module_id}.headline",
                f"{module_label} headline",
                original_module.headline,
                improved_module.headline,
            )
            add_change(
                f"modules.{improved_module.module_id}.body",
                f"{module_label} body",
                original_module.body,
                improved_module.body,
            )
            max_bullets = max(len(original_module.bullets), len(improved_module.bullets))
            for bullet_index in range(max_bullets):
                before = original_module.bullets[bullet_index] if bullet_index < len(original_module.bullets) else ""
                after = improved_module.bullets[bullet_index] if bullet_index < len(improved_module.bullets) else ""
                add_change(
                    f"modules.{improved_module.module_id}.bullets[{bullet_index}]",
                    f"{module_label} bullet {bullet_index + 1}",
                    before,
                    after,
                )

        return changes

    def _create_publish_job(self, *, draft_id: UUID, created_at: datetime):
        from app.models.entities import AplusPublishJob

        return AplusPublishJob(
            draft_id=draft_id,
            status="draft",
            created_at=created_at,
        )

    def _get_latest_publish_job_record(self, *, draft_id: UUID):
        from app.models.entities import AplusPublishJob

        return self.db_session.execute(
            select(AplusPublishJob)
            .where(AplusPublishJob.draft_id == draft_id)
            .order_by(AplusPublishJob.created_at.desc())
        ).scalar_one_or_none()

    def _refresh_publish_job_status(self, *, draft: AplusDraft, publish_job) -> None:
        if not publish_job.external_submission_id:
            return
        product = self._get_product(draft.product_id)
        try:
            content_status = self.amazon_service.get_aplus_content_document(
                marketplace_id=product.marketplace_id,
                content_reference_key=publish_job.external_submission_id,
                included_data_set=["METADATA"],
            )
        except AmazonRequestError as exc:
            publish_job.error_message = str(exc)[:1024]
            return

        response_payload = dict(publish_job.response_payload or {})
        response_payload["contentRecord"] = content_status.get("contentRecord")
        response_payload["warnings"] = content_status.get("warnings") or []
        response_payload["errors"] = content_status.get("errors") or []
        response_payload["statusRefresh"] = {
            "checkedAt": self._now().isoformat(),
        }
        publish_job.response_payload = response_payload

        content_metadata = (content_status.get("contentRecord") or {}).get("contentMetadata") or {}
        amazon_status = str(content_metadata.get("status") or "").upper()
        if amazon_status == "APPROVED":
            publish_job.status = "approved"
            publish_job.completed_at = self._now()
            draft.status = DraftStatus.PUBLISHED.value
            publish_job.error_message = None
        elif amazon_status == "REJECTED":
            publish_job.status = "rejected"
            publish_job.completed_at = self._now()
            draft.status = DraftStatus.FAILED.value
            reasons = self._extract_publish_job_messages(response_payload, key="errors")
            publish_job.error_message = "; ".join(reasons[:3]) if reasons else "Amazon rejected the A+ content document."
        elif amazon_status == "SUBMITTED":
            publish_job.status = "in_review"
            draft.status = DraftStatus.READY_TO_PUBLISH.value
        elif amazon_status == "DRAFT":
            publish_job.status = "submitted"
            draft.status = DraftStatus.READY_TO_PUBLISH.value

    def _set_publish_job_state(
        self,
        *,
        publish_job,
        status: str,
        response_payload: dict[str, object],
    ) -> None:
        current_payload = dict(publish_job.response_payload or {})
        current_payload.update(response_payload)
        publish_job.status = status
        publish_job.response_payload = current_payload
        self.db_session.commit()
        self.db_session.refresh(publish_job)

    @staticmethod
    def _extract_publish_job_messages(response_payload: dict[str, object], *, key: str) -> list[str]:
        values = response_payload.get(key)
        if not isinstance(values, list):
            return []
        messages: list[str] = []
        for item in values:
            if isinstance(item, str):
                messages.append(item)
                continue
            if isinstance(item, dict):
                message = item.get("message") or item.get("details") or item.get("code")
                if isinstance(message, str):
                    messages.append(message)
        return messages[:10]

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)
