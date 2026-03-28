from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_current_user, get_product_service
from app.models.entities import User
from app.schemas.product import (
    ProductListResponse,
    ProductMutationResponse,
    ProductPriceUpdateRequest,
    ProductStockUpdateRequest,
)
from app.services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=ProductListResponse)
def read_products(
    _: User = Depends(get_current_user),
    product_service: ProductService = Depends(get_product_service),
) -> ProductListResponse:
    return product_service.list_products()


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
