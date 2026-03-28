from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import AplusDraft, AplusPublishJob, Product, User
from app.models.enums import DraftStatus, JobStatus
from app.schemas.aplus import (
    AplusDraftListResponse,
    AplusDraftPayload,
    AplusDraftResponse,
    AplusPublishResponse,
)
from app.services.ai.openai_service import OpenAiAplusService
from app.services.amazon.service import AmazonSpApiService
from app.services.notification_service import NotificationService
from app.services.product_service import ProductService


class AplusService:
    def __init__(
        self,
        db_session: Session,
        amazon_service: AmazonSpApiService,
        openai_service: OpenAiAplusService,
    ) -> None:
        self.db_session = db_session
        self.amazon_service = amazon_service
        self.openai_service = openai_service

    def list_drafts(self) -> AplusDraftListResponse:
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
        requested_by: User,
    ) -> AplusDraftResponse:
        product = self._get_product(product_id)
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
        )

        draft = AplusDraft(
            product_id=product.id,
            status=DraftStatus.DRAFT.value,
            brand_tone=brand_tone,
            positioning=positioning,
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
        draft.validated_payload = draft_payload.model_dump(mode="json")
        draft.status = DraftStatus.VALIDATED.value
        self.db_session.commit()
        self.db_session.refresh(draft)
        return self._serialize_draft(draft=draft, product=product)

    def publish_draft(self, *, draft_id: UUID) -> AplusPublishResponse:
        draft = self._get_draft(draft_id)
        product = self._get_product(draft.product_id)
        notification_service = NotificationService(self.db_session)
        timestamp = self._now()

        try:
            validated_payload = AplusDraftPayload.model_validate(
                draft.validated_payload or draft.draft_payload
            )
            prepared_payload = self._build_amazon_payload(product=product, draft_payload=validated_payload)

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
    ) -> dict[str, object]:
        locale = self._marketplace_locale(product.marketplace_id)
        content_modules = []
        for module in draft_payload.modules:
            content_modules.append(
                {
                    "contentModuleType": self._amazon_module_type(module.module_type),
                    "headline": module.headline,
                    "body": module.body,
                    "bullets": module.bullets,
                    "imageBrief": module.image_brief,
                }
            )

        amazon_content = {
            "contentDocument": {
                "name": f"{product.title} A+ draft",
                "locale": locale,
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
    def _amazon_module_type(module_type: str) -> str:
        mapping = {
            "hero": "STANDARD_HEADER_IMAGE_TEXT",
            "feature": "STANDARD_SINGLE_IMAGE_HIGHLIGHTS",
            "comparison": "STANDARD_COMPARISON_TABLE",
            "faq": "STANDARD_TEXT",
        }
        return mapping.get(module_type, "STANDARD_SINGLE_IMAGE_HIGHLIGHTS")

    @staticmethod
    def _marketplace_locale(marketplace_id: str) -> str:
        mapping = {
            "A1PA6795UKMFR9": "de-DE",
            "ATVPDKIKX0DER": "en-US",
            "A1F83G8C2ARO7P": "en-GB",
        }
        return mapping.get(marketplace_id, "en-US")

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
    def _serialize_draft(*, draft: AplusDraft, product: Product) -> AplusDraftResponse:
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
            draft_payload=AplusDraftPayload.model_validate(draft.draft_payload),
            validated_payload=(
                AplusDraftPayload.model_validate(draft.validated_payload)
                if draft.validated_payload is not None
                else None
            ),
            created_at=draft.created_at,
            updated_at=draft.updated_at,
        )

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)
