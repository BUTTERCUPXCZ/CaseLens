"""The background jobs, as Dramatiq actors. A worker runs:

    dramatiq caselens.infrastructure.queue.actors --queues lawphil --processes 1 --threads 1
    dramatiq caselens.infrastructure.queue.actors --queues digests --processes 1 --threads 4

Delivery is at-least-once: RabbitMQ gives a job to another worker if the first one dies before finishing.
So each job is safe to run twice (ingesting a case that is stored is ignored, a catalog build carries on
where it stopped, a digest only fills the answers still pending). The work itself is in `jobs.py`; these only add the queue, retries and time limits.
"""
import logging

import dramatiq

from caselens.infrastructure.config import get_settings
from caselens.infrastructure.queue import jobs
from caselens.infrastructure.queue.broker import DIGEST_QUEUE, LAWPHIL_QUEUE, build_broker

broker = build_broker(get_settings())
dramatiq.set_broker(broker)  # the actors below attach to it

logger = logging.getLogger(__name__)

_MINUTE = 60_000  # Dramatiq counts time in milliseconds
# A failure that is not a DomainError (a database blip, a network error) is tried again after 15 s, 1 min, 4 min;
# after the last try the message waits in the dead-letter queue (`<queue>.XQ`) to be looked at.
_RETRIES = {"max_retries": 3, "min_backoff": 15_000, "max_backoff": 5 * _MINUTE}


def _setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


@dramatiq.actor(queue_name=LAWPHIL_QUEUE, time_limit=15 * _MINUTE, **_RETRIES)
def resolve_upload(upload_id: int) -> None:
    _setup_logging()
    jobs.resolve_upload(upload_id)


@dramatiq.actor(queue_name=LAWPHIL_QUEUE, time_limit=15 * _MINUTE, **_RETRIES)
def fetch_case(gr_no: str, year: int | None) -> None:
    _setup_logging()
    jobs.fetch_case(gr_no, year)


@dramatiq.actor(queue_name=LAWPHIL_QUEUE, time_limit=60 * _MINUTE, max_retries=1, min_backoff=_MINUTE)
def build_catalog(first_year: int) -> None:
    _setup_logging()
    jobs.build_catalog(first_year)


@dramatiq.actor(queue_name=LAWPHIL_QUEUE, time_limit=60 * _MINUTE, max_retries=1, min_backoff=_MINUTE)
def refresh_catalog() -> None:
    _setup_logging()
    jobs.refresh_catalog()


@dramatiq.actor(queue_name=DIGEST_QUEUE, time_limit=15 * _MINUTE, **_RETRIES)
def build_digest(digest_id: int, keys: list[str] | None = None) -> None:
    _setup_logging()
    jobs.build_digest(digest_id, keys)
