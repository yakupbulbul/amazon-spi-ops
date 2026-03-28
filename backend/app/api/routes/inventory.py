from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_current_user, get_inventory_service
from app.models.entities import User
from app.schemas.inventory import (
    InventoryAlertListResponse,
    InventoryListResponse,
    InventorySyncResponse,
)
from app.services.inventory_service import InventoryService

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("", response_model=InventoryListResponse)
def read_inventory(
    _: User = Depends(get_current_user),
    inventory_service: InventoryService = Depends(get_inventory_service),
) -> InventoryListResponse:
    return inventory_service.list_inventory()


@router.get("/alerts", response_model=InventoryAlertListResponse)
def read_inventory_alerts(
    _: User = Depends(get_current_user),
    inventory_service: InventoryService = Depends(get_inventory_service),
) -> InventoryAlertListResponse:
    return inventory_service.list_alerts()


@router.post("/sync", response_model=InventorySyncResponse)
def sync_inventory(
    _: User = Depends(get_current_user),
    inventory_service: InventoryService = Depends(get_inventory_service),
) -> InventorySyncResponse:
    try:
        return inventory_service.sync_inventory()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
