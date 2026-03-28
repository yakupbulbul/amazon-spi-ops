from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from app.api.dependencies import (
    get_aplus_asset_service,
    get_aplus_image_service,
    get_aplus_service,
    get_current_user,
)
from app.models.entities import User
from app.schemas.aplus import (
    AplusAssetListResponse,
    AplusAssetResponse,
    AplusDraftListResponse,
    AplusDraftResponse,
    AplusGenerateImageRequest,
    AplusGenerateRequest,
    AplusPublishRequest,
    AplusPublishResponse,
    AplusValidateRequest,
)
from app.services.aplus_image_service import AplusImageService
from app.services.aplus_asset_service import AplusAssetService
from app.services.aplus_service import AplusService
from app.workers.main import generate_aplus_module_image

router = APIRouter(prefix="/aplus", tags=["aplus"])


@router.get("/drafts", response_model=AplusDraftListResponse)
def read_aplus_drafts(
    _: User = Depends(get_current_user),
    aplus_service: AplusService = Depends(get_aplus_service),
) -> AplusDraftListResponse:
    return aplus_service.list_drafts()


@router.get("/assets", response_model=AplusAssetListResponse)
def read_aplus_assets(
    product_id: str | None = Query(default=None),
    _: User = Depends(get_current_user),
    asset_service: AplusAssetService = Depends(get_aplus_asset_service),
) -> AplusAssetListResponse:
    try:
        return asset_service.list_assets(
            product_id=UUID(product_id) if product_id else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.post("/assets/upload", response_model=AplusAssetResponse)
async def upload_aplus_asset(
    file: UploadFile = File(...),
    asset_scope: str = Form(...),
    product_id: str | None = Form(default=None),
    label: str | None = Form(default=None),
    current_user: User = Depends(get_current_user),
    asset_service: AplusAssetService = Depends(get_aplus_asset_service),
) -> AplusAssetResponse:
    try:
        return await asset_service.upload_asset(
            file=file,
            asset_scope=asset_scope,
            label=label,
            product_id=UUID(product_id) if product_id else None,
            uploaded_by=current_user,
        )
    except ValueError as exc:
        detail = str(exc)
        if detail == "Product not found.":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail) from exc
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail) from exc


@router.post("/generate", response_model=AplusDraftResponse)
def generate_aplus_draft(
    payload: AplusGenerateRequest,
    current_user: User = Depends(get_current_user),
    aplus_service: AplusService = Depends(get_aplus_service),
) -> AplusDraftResponse:
    try:
        return aplus_service.generate_draft(
            product_id=UUID(payload.product_id),
            brand_tone=payload.brand_tone,
            positioning=payload.positioning,
            source_language=payload.source_language,
            target_language=payload.target_language,
            auto_translate=payload.auto_translate,
            requested_by=current_user,
        )
    except ValueError as exc:
        detail = str(exc)
        if detail == "Product not found.":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail) from exc
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.post("/images/generate", response_model=AplusDraftResponse)
def queue_aplus_image_generation(
    payload: AplusGenerateImageRequest,
    current_user: User = Depends(get_current_user),
    image_service: AplusImageService = Depends(get_aplus_image_service),
) -> AplusDraftResponse:
    try:
        draft = image_service.queue_image_generation(
            draft_id=UUID(payload.draft_id),
            module_index=payload.module_index,
            image_prompt=payload.image_prompt,
            overlay_text=payload.overlay_text,
            reference_asset_ids=payload.reference_asset_ids,
            requested_by=current_user,
        )
        generate_aplus_module_image.send(payload.draft_id, payload.module_index, str(current_user.id))
        return draft
    except ValueError as exc:
        detail = str(exc)
        if detail in {"A+ draft not found.", "Product not found."}:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail) from exc
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail) from exc


@router.post("/validate", response_model=AplusDraftResponse)
def validate_aplus_draft(
    payload: AplusValidateRequest,
    _: User = Depends(get_current_user),
    aplus_service: AplusService = Depends(get_aplus_service),
) -> AplusDraftResponse:
    try:
        return aplus_service.validate_draft(
            draft_id=UUID(payload.draft_id),
            draft_payload=payload.draft_payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/publish", response_model=AplusPublishResponse)
def publish_aplus_draft(
    payload: AplusPublishRequest,
    _: User = Depends(get_current_user),
    aplus_service: AplusService = Depends(get_aplus_service),
) -> AplusPublishResponse:
    try:
        return aplus_service.publish_draft(draft_id=UUID(payload.draft_id))
    except ValueError as exc:
        detail = str(exc)
        if detail == "A+ draft not found.":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail) from exc
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
