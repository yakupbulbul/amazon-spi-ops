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
    AplusModulePayload,
    AplusPublishResponse,
    SupportedAplusLanguage,
)
from app.services.ai.openai_service import OpenAiAplusService
from app.services.aplus_optimization import build_aplus_optimization_report
from app.services.aplus_readiness import build_aplus_readiness_report
from app.services.amazon.aplus_contract import AmazonContractMapper, PreparedAmazonImageAsset
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

            prepared_payload = self._publish_to_amazon(
                product=product,
                draft_payload=validated_payload,
                target_language=draft.target_language,
            )

            from app.models.entities import AplusPublishJob

            publish_job = AplusPublishJob(
                draft_id=draft.id,
                status=JobStatus.SUCCEEDED.value,
                external_submission_id=str(prepared_payload["contentReferenceKey"]),
                submitted_at=timestamp,
                completed_at=timestamp,
                created_at=timestamp,
            )
            self.db_session.add(publish_job)
            draft.status = DraftStatus.READY_TO_PUBLISH.value
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
                    "Submitted the A+ content document to Amazon for review using the supported real publish subset."
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

    def _publish_to_amazon(
        self,
        *,
        product: Product,
        draft_payload: AplusDraftPayload,
        target_language: str,
    ) -> dict[str, object]:
        locale = target_language or self._marketplace_locale(product.marketplace_id)
        prepared_assets = self._prepare_amazon_assets(
            product=product,
            draft_payload=draft_payload,
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
            return PreparedAmazonImageAsset(
                upload_destination_id=str(cached_upload["upload_destination_id"]),
                alt_text=module.image_brief.strip(),
                width_pixels=int(cached_upload["width_pixels"]),
                height_pixels=int(cached_upload["height_pixels"]),
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
