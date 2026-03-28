from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.models.entities import User
from app.services.auth_service import AuthService
from app.services.dashboard_service import DashboardService
from app.services.user_service import UserService

bearer_scheme = HTTPBearer(auto_error=False)


def get_auth_service(db_session: Session = Depends(get_db_session)) -> AuthService:
    return AuthService(db_session)


def get_user_service(db_session: Session = Depends(get_db_session)) -> UserService:
    return UserService(db_session)


def get_dashboard_service(db_session: Session = Depends(get_db_session)) -> DashboardService:
    return DashboardService(db_session)


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
