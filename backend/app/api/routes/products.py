from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user, get_product_service
from app.models.entities import User
from app.schemas.product import ProductListResponse
from app.services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=ProductListResponse)
def read_products(
    _: User = Depends(get_current_user),
    product_service: ProductService = Depends(get_product_service),
) -> ProductListResponse:
    return product_service.list_products()
