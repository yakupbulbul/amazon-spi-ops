from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db_session
from app.models.entities import User
from app.services.ai.openai_service import OpenAiAplusService
from app.services.aplus_asset_service import AplusAssetService
from app.services.aplus_service import AplusService
from app.services.amazon.service import AmazonSpApiService
from app.services.auth_service import AuthService
from app.services.catalog_import_service import CatalogImportService
from app.services.dashboard_service import DashboardService
from app.services.inventory_service import InventoryService
from app.services.notification_service import NotificationService
from app.services.product_service import ProductService
from app.services.user_service import UserService
from app.services.media_storage import MediaStorageService

bearer_scheme = HTTPBearer(auto_error=False)


def get_auth_service(db_session: Session = Depends(get_db_session)) -> AuthService:
    return AuthService(db_session)


def get_user_service(db_session: Session = Depends(get_db_session)) -> UserService:
    return UserService(db_session)


def get_dashboard_service(db_session: Session = Depends(get_db_session)) -> DashboardService:
    return DashboardService(db_session)


def get_amazon_service() -> AmazonSpApiService:
    return AmazonSpApiService()


def get_openai_aplus_service() -> OpenAiAplusService:
    return OpenAiAplusService()


def get_media_storage_service() -> MediaStorageService:
    return MediaStorageService()


def get_aplus_service(
    db_session: Session = Depends(get_db_session),
    amazon_service: AmazonSpApiService = Depends(get_amazon_service),
    openai_service: OpenAiAplusService = Depends(get_openai_aplus_service),
) -> AplusService:
    return AplusService(db_session, amazon_service, openai_service)


def get_aplus_asset_service(
    db_session: Session = Depends(get_db_session),
    storage_service: MediaStorageService = Depends(get_media_storage_service),
) -> AplusAssetService:
    return AplusAssetService(
        db_session,
        storage_service,
        max_upload_bytes=settings.aplus_upload_max_bytes,
    )


def get_notification_service(
    db_session: Session = Depends(get_db_session),
) -> NotificationService:
    return NotificationService(db_session)


def get_product_service(db_session: Session = Depends(get_db_session)) -> ProductService:
    return ProductService(db_session, AmazonSpApiService())


def get_catalog_import_service(
    db_session: Session = Depends(get_db_session),
    amazon_service: AmazonSpApiService = Depends(get_amazon_service),
) -> CatalogImportService:
    return CatalogImportService(db_session, amazon_service)


def get_inventory_service(
    db_session: Session = Depends(get_db_session),
    amazon_service: AmazonSpApiService = Depends(get_amazon_service),
) -> InventoryService:
    return InventoryService(db_session, amazon_service)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    user = auth_service.get_user_from_token(credentials.credentials)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    return user
