from __future__ import annotations

import logging

from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.entities import User
from app.models.enums import UserRole

logger = logging.getLogger(__name__)


def bootstrap_admin_user() -> None:
    with SessionLocal() as session:
        existing_user = session.scalar(select(User).where(User.email == settings.admin_email))
        if existing_user is not None:
            return

        session.add(
            User(
                email=settings.admin_email,
                hashed_password=hash_password(settings.admin_password),
                full_name="Local Admin",
                role=UserRole.ADMIN.value,
                is_active=True,
            )
        )
        session.commit()
        logger.info("Bootstrapped local admin user for %s", settings.admin_email)

