from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import User


class UserService:
    def __init__(self, db_session: Session) -> None:
        self.db_session = db_session

    def get_user_by_email(self, email: str) -> User | None:
        return self.db_session.scalar(select(User).where(User.email == email))

