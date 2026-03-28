from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.entities import AplusAsset, Product, User
from app.schemas.aplus import AplusAssetListResponse, AplusAssetResponse
from app.services.media_storage import MediaStorageService

ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


class AplusAssetService:
    def __init__(
        self,
        db_session: Session,
        storage_service: MediaStorageService,
        max_upload_bytes: int,
    ) -> None:
        self.db_session = db_session
        self.storage_service = storage_service
        self.max_upload_bytes = max_upload_bytes

    def list_assets(self, *, product_id: UUID | None = None) -> AplusAssetListResponse:
        statement = select(AplusAsset).order_by(AplusAsset.created_at.desc())
        if product_id is not None:
            statement = statement.where(
                or_(AplusAsset.product_id == product_id, AplusAsset.product_id.is_(None))
            )

        assets = self.db_session.execute(statement).scalars().all()
        return AplusAssetListResponse(items=[self._serialize_asset(asset) for asset in assets])

    async def upload_asset(
        self,
        *,
        file: UploadFile,
        asset_scope: str,
        label: str | None,
        product_id: UUID | None,
        uploaded_by: User,
    ) -> AplusAssetResponse:
        if asset_scope not in {"product", "brand", "logo", "generated"}:
            raise ValueError("Unsupported asset scope.")

        if file.content_type not in ALLOWED_IMAGE_TYPES:
            raise ValueError("Only JPG, PNG, and WEBP images are supported.")

        content = await file.read()
        if not content:
            raise ValueError("Uploaded asset is empty.")
        if len(content) > self.max_upload_bytes:
            raise ValueError("Uploaded asset exceeds the configured size limit.")

        product: Product | None = None
        if product_id is not None:
            product = self.db_session.get(Product, product_id)
            if product is None:
                raise ValueError("Product not found.")

        suffix = self._resolve_suffix(
            original_name=file.filename,
            mime_type=file.content_type,
        )
        _, public_url = self.storage_service.store_bytes(
            subdirectory="aplus-assets",
            suffix=suffix,
            content=content,
        )

        asset = AplusAsset(
            product_id=product.id if product is not None else None,
            created_by_id=uploaded_by.id,
            asset_scope=asset_scope,
            label=label or Path(file.filename or "asset").stem,
            file_name=file.filename or f"asset{suffix}",
            mime_type=file.content_type,
            file_size_bytes=len(content),
            public_url=public_url,
            asset_metadata={
                "product_title": product.title if product is not None else None,
                "brand": product.brand if product is not None else None,
            },
            created_at=self._now(),
        )
        self.db_session.add(asset)
        self.db_session.commit()
        self.db_session.refresh(asset)
        return self._serialize_asset(asset)

    @staticmethod
    def _resolve_suffix(*, original_name: str | None, mime_type: str) -> str:
        candidate = Path(original_name or "").suffix.lower()
        if candidate in {".jpg", ".jpeg", ".png", ".webp"}:
            return ".jpg" if candidate == ".jpeg" else candidate
        return ALLOWED_IMAGE_TYPES[mime_type]

    @staticmethod
    def _serialize_asset(asset: AplusAsset) -> AplusAssetResponse:
        return AplusAssetResponse(
            id=str(asset.id),
            product_id=str(asset.product_id) if asset.product_id is not None else None,
            asset_scope=asset.asset_scope,  # type: ignore[arg-type]
            label=asset.label,
            file_name=asset.file_name,
            mime_type=asset.mime_type,
            file_size_bytes=asset.file_size_bytes,
            public_url=asset.public_url,
            created_at=asset.created_at,
        )

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)
