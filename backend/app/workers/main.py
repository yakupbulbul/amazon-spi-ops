import logging
import time
from uuid import UUID

import dramatiq
from dramatiq.brokers.redis import RedisBroker

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.logging import configure_logging
from app.services.amazon.service import AmazonSpApiService
from app.services.catalog_import_service import CatalogImportService
from app.services.notification_service import NotificationService

configure_logging()

broker = RedisBroker(url=settings.redis_url)
dramatiq.set_broker(broker)

logger = logging.getLogger(__name__)


@dramatiq.actor
def heartbeat() -> None:
    logger.info("worker heartbeat")


@dramatiq.actor(queue_name="catalog-import")
def import_amazon_catalog(job_id: str) -> None:
    with SessionLocal() as session:
        CatalogImportService(session, AmazonSpApiService()).run_import_job(UUID(job_id))


@dramatiq.actor(queue_name="notifications")
def dispatch_slack_notification(notification_id: str) -> None:
    with SessionLocal() as session:
        NotificationService(session).deliver_slack_notification(UUID(notification_id))


def main() -> None:
    logger.info("worker bootstrap completed; waiting for Dramatiq process manager")
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()
