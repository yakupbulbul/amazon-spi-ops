from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import CatalogImportJob, InventorySnapshot, Product, User
from app.models.enums import CatalogImportStatus, InventoryAlertStatus, ProductSource
from app.schemas.product import CatalogImportJobResponse
from app.services.amazon.mappers import AmazonListingImportRecord, map_search_listings_item
from app.services.amazon.service import AmazonSpApiService


@dataclass(frozen=True)
class ImportPageResult:
    created_count: int
    updated_count: int
    skipped_count: int
    error_count: int


class CatalogImportService:
    def __init__(self, db_session: Session, amazon_service: AmazonSpApiService) -> None:
        self.db_session = db_session
        self.amazon_service = amazon_service

    def create_import_job(self, *, created_by: User) -> CatalogImportJobResponse:
        active_job = self._get_active_job()
        if active_job is not None:
            raise ValueError("A catalog import is already in progress.")

        job = CatalogImportJob(
            status=CatalogImportStatus.PENDING.value,
            source="amazon_sp_api",
            marketplace_id=self.amazon_service.settings.marketplace_id,
            created_count=0,
            updated_count=0,
            skipped_count=0,
            error_count=0,
            created_by_id=created_by.id,
            created_at=self._now(),
        )
        self.db_session.add(job)
        self.db_session.commit()
        self.db_session.refresh(job)
        return self._serialize_job(job)

    def get_latest_job(self) -> CatalogImportJobResponse | None:
        job = self.db_session.execute(
            select(CatalogImportJob).order_by(CatalogImportJob.created_at.desc()).limit(1)
        ).scalar_one_or_none()
        if job is None:
            return None
        return self._serialize_job(job)

    def run_import_job(self, job_id: UUID) -> None:
        job = self.db_session.get(CatalogImportJob, job_id)
        if job is None:
            raise ValueError("Catalog import job not found.")

        if job.status == CatalogImportStatus.RUNNING.value:
            return

        imported_listing_count = 0
        job.status = CatalogImportStatus.RUNNING.value
        job.started_at = self._now()
        job.completed_at = None
        job.error_message = None
        self.db_session.commit()

        try:
            next_token: str | None = None

            while True:
                payload = self.amazon_service.search_listings_items(
                    marketplace_id=job.marketplace_id,
                    next_token=next_token,
                    page_size=50,
                )
                total_expected = payload.get("numberOfResults")
                if isinstance(total_expected, int):
                    job.total_expected = total_expected

                page_result = self._import_page(
                    payload=payload,
                    marketplace_id=job.marketplace_id,
                )
                imported_listing_count += page_result.created_count + page_result.updated_count
                job.created_count += page_result.created_count
                job.updated_count += page_result.updated_count
                job.skipped_count += page_result.skipped_count
                job.error_count += page_result.error_count
                self.db_session.commit()

                next_token = self._extract_next_token(payload)
                if not next_token:
                    break

            if imported_listing_count > 0:
                self._cleanup_sample_products()
                self.db_session.commit()

            job.status = CatalogImportStatus.SUCCEEDED.value
            job.completed_at = self._now()
            self.db_session.commit()
        except Exception as exc:
            self.db_session.rollback()
            job = self.db_session.get(CatalogImportJob, job_id)
            if job is not None:
                job.status = CatalogImportStatus.FAILED.value
                job.completed_at = self._now()
                job.error_message = str(exc)
                self.db_session.commit()
            raise

    def _import_page(self, *, payload: dict[str, object], marketplace_id: str) -> ImportPageResult:
        items = payload.get("items")
        if not isinstance(items, list):
            return ImportPageResult(created_count=0, updated_count=0, skipped_count=0, error_count=0)

        created_count = 0
        updated_count = 0
        skipped_count = 0
        error_count = 0

        for item in items:
            if not isinstance(item, dict):
                skipped_count += 1
                continue

            record = map_search_listings_item(item, marketplace_id=marketplace_id)
            if record is None:
                skipped_count += 1
                continue

            try:
                created = self._upsert_product(record=record, marketplace_id=marketplace_id)
                if created:
                    created_count += 1
                else:
                    updated_count += 1
            except Exception:
                error_count += 1

        return ImportPageResult(
            created_count=created_count,
            updated_count=updated_count,
            skipped_count=skipped_count,
            error_count=error_count,
        )

    def _upsert_product(self, *, record: AmazonListingImportRecord, marketplace_id: str) -> bool:
        product = self.db_session.execute(
            select(Product).where((Product.sku == record.sku) | (Product.asin == record.asin)).limit(1)
        ).scalar_one_or_none()
        created = product is None

        if product is None:
            product = Product(
                sku=record.sku,
                asin=record.asin,
                title=record.title,
                brand=record.brand,
                source=ProductSource.AMAZON_LISTING.value,
                marketplace_id=marketplace_id,
                price_amount=record.price_amount,
                price_currency=record.price_currency,
                low_stock_threshold=10,
                is_active=record.is_active,
            )
            self.db_session.add(product)
            self.db_session.flush()
        else:
            product.sku = record.sku
            product.asin = record.asin
            product.title = record.title
            product.marketplace_id = marketplace_id
            product.source = ProductSource.AMAZON_LISTING.value
            product.is_active = record.is_active
            if record.brand:
                product.brand = record.brand
            if record.price_amount is not None:
                product.price_amount = record.price_amount
            if record.price_currency:
                product.price_currency = record.price_currency
            self.db_session.flush()

        if record.quantity is not None:
            self._create_inventory_snapshot(product=product, quantity=record.quantity)

        return created

    def _create_inventory_snapshot(self, *, product: Product, quantity: int) -> None:
        snapshot = InventorySnapshot(
            product_id=product.id,
            available_quantity=quantity,
            reserved_quantity=0,
            inbound_quantity=0,
            alert_status=self._determine_alert_status(
                available_quantity=quantity,
                threshold=product.low_stock_threshold,
            ),
            captured_at=self._now(),
        )
        self.db_session.add(snapshot)

    def _cleanup_sample_products(self) -> None:
        sample_products = self.db_session.execute(
            select(Product).where(Product.source == ProductSource.SAMPLE.value)
        ).scalars().all()
        for product in sample_products:
            self.db_session.delete(product)

    def _get_active_job(self) -> CatalogImportJob | None:
        return self.db_session.execute(
            select(CatalogImportJob)
            .where(
                CatalogImportJob.status.in_(
                    [CatalogImportStatus.PENDING.value, CatalogImportStatus.RUNNING.value]
                )
            )
            .order_by(CatalogImportJob.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()

    @staticmethod
    def _extract_next_token(payload: dict[str, object]) -> str | None:
        pagination = payload.get("pagination")
        if not isinstance(pagination, dict):
            return None
        next_token = pagination.get("nextToken")
        if isinstance(next_token, str) and next_token:
            return next_token
        return None

    @staticmethod
    def _determine_alert_status(*, available_quantity: int, threshold: int) -> str:
        if available_quantity <= 0:
            return InventoryAlertStatus.OUT_OF_STOCK.value
        if available_quantity <= threshold:
            return InventoryAlertStatus.LOW.value
        return InventoryAlertStatus.HEALTHY.value

    @staticmethod
    def _serialize_job(job: CatalogImportJob) -> CatalogImportJobResponse:
        processed_count = job.created_count + job.updated_count + job.skipped_count + job.error_count
        return CatalogImportJobResponse(
            id=str(job.id),
            status=job.status,
            source=job.source,
            marketplace_id=job.marketplace_id,
            created_count=job.created_count,
            updated_count=job.updated_count,
            skipped_count=job.skipped_count,
            error_count=job.error_count,
            processed_count=processed_count,
            total_expected=job.total_expected,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error_message=job.error_message,
            created_at=job.created_at,
        )

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)
