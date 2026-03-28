from __future__ import annotations

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def run_migrations() -> None:
    alembic_config = Config(str(BACKEND_ROOT / "alembic.ini"))
    alembic_config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))

    try:
        command.upgrade(alembic_config, "head")
    except SQLAlchemyError:
        logger.exception("Unable to apply migrations during startup")
        raise

