from __future__ import annotations

import uuid
from datetime import timedelta

import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, decode_access_token, verify_password
from app.models.entities import User


class AuthService:
    def __init__(self, db_session: Session) -> None:
        self.db_session = db_session

    def authenticate_user(self, email: str, password: str) -> User | None:
        user = self.db_session.scalar(select(User).where(User.email == email))
        if user is None or not user.is_active:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    def create_access_token(self, user: User) -> str:
        return create_access_token(
            subject=str(user.id),
            expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
        )

    def get_user_from_token(self, token: str) -> User | None:
        try:
            payload = decode_access_token(token)
        except jwt.InvalidTokenError:
            return None

        subject = payload.get("sub")
        if not subject:
            return None

        try:
            user_id = uuid.UUID(subject)
        except ValueError:
            return None

        return self.db_session.get(User, user_id)
