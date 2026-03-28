import logging
import time

import dramatiq
from dramatiq.brokers.redis import RedisBroker

from app.core.config import settings
from app.core.logging import configure_logging

configure_logging()

broker = RedisBroker(url=settings.redis_url)
dramatiq.set_broker(broker)

logger = logging.getLogger(__name__)


@dramatiq.actor
def heartbeat() -> None:
    logger.info("worker heartbeat")


def main() -> None:
    logger.info("worker bootstrap completed; waiting for Dramatiq process manager")
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()

