from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_current_user, get_product_service
from app.models.entities import User
from app.schemas.product import (
    CatalogImportJobResponse,
    ProductListResponse,
    ProductMutationResponse,
    ProductPriceUpdateRequest,
    ProductStockUpdateRequest,
)
from app.services.product_service import ProductService
from app.workers.main import import_amazon_catalog

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=ProductListResponse)
def read_products(
    _: User = Depends(get_current_user),
    product_service: ProductService = Depends(get_product_service),
) -> ProductListResponse:
    return product_service.list_products()


@router.post("/import", response_model=CatalogImportJobResponse)
def import_products(
    current_user: User = Depends(get_current_user),
    product_service: ProductService = Depends(get_product_service),
) -> CatalogImportJobResponse:
    try:
        job = product_service.create_import_job(requested_by=current_user)
        import_amazon_catalog.send(job.id)
        return job
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.get("/import-jobs/latest", response_model=CatalogImportJobResponse | None)
def read_latest_import_job(
    _: User = Depends(get_current_user),
    product_service: ProductService = Depends(get_product_service),
) -> CatalogImportJobResponse | None:
    return product_service.get_latest_import_job()


@router.patch("/{product_id}/price", response_model=ProductMutationResponse)
def update_product_price(
    product_id: UUID,
    payload: ProductPriceUpdateRequest,
    current_user: User = Depends(get_current_user),
    product_service: ProductService = Depends(get_product_service),
) -> ProductMutationResponse:
    try:
        return product_service.update_price(
            product_id=product_id,
            price_amount=payload.price_amount,
            price_currency=payload.price_currency,
            requested_by=current_user,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.patch("/{product_id}/stock", response_model=ProductMutationResponse)
def update_product_stock(
    product_id: UUID,
    payload: ProductStockUpdateRequest,
    current_user: User = Depends(get_current_user),
    product_service: ProductService = Depends(get_product_service),
) -> ProductMutationResponse:
    try:
        return product_service.update_stock(
            product_id=product_id,
            quantity=payload.quantity,
            requested_by=current_user,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
