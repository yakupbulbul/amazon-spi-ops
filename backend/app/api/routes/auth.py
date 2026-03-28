from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_auth_service, get_current_user
from app.models.entities import User
from app.schemas.auth import AuthTokenResponse, LoginRequest, UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=AuthTokenResponse)
def login(payload: LoginRequest, auth_service: AuthService = Depends(get_auth_service)) -> AuthTokenResponse:
    authenticated_user = auth_service.authenticate_user(payload.email, payload.password)
    if authenticated_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = auth_service.create_access_token(authenticated_user)
    return AuthTokenResponse(access_token=token, user=UserResponse.model_validate(authenticated_user))


@router.get("/me", response_model=UserResponse)
def read_current_user(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)

