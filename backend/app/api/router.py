from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.health import router as health_router
from app.api.routes.inventory import router as inventory_router
from app.api.routes.products import router as products_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(dashboard_router)
api_router.include_router(health_router, tags=["health"])
api_router.include_router(inventory_router)
api_router.include_router(products_router)
