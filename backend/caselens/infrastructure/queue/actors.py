"""The background jobs, as Dramatiq actors. A worker runs:

    dramatiq caselens.infrastructure.queue.actors --queues lawphil --processes 1 --threads 1
    dramatiq caselens.infrastructure.queue.actors --queues digests --processes 1 --threads 4

Delivery is at-least-once: RabbitMQ gives a job to another worker if the first one dies before finishing.
So each job is safe to run twice (ingesting a case that is stored is ignored, a catalog build carries on
where it stopped, a digest only fills the answers still pending). Each builds its own services and
database session, like the RQ jobs they replace.
"""
import logging

import dramatiq

from caselens.composition import Services
from caselens.domain.errors import DomainError
from caselens.domain.value_objects import GrNumber
from caselens.infrastructure.config import get_settings
from caselens.infrastructure.db.job_lock_repository import SqlJobLockRepository
from caselens.infrastructure.db.session import SessionLocal, engine
from caselens.infrastructure.queue import lock_keys
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
    with SessionLocal() as session:
        Services(session).resolve_upload_citations().execute(upload_id)


@dramatiq.actor(queue_name=LAWPHIL_QUEUE, time_limit=15 * _MINUTE, **_RETRIES)
def fetch_case(gr_no: str, year: int | None) -> None:
    _setup_logging()
    with SessionLocal() as session:
        try:
            Services(session).fetch_case_by_gr_number().execute(GrNumber(gr_no), year)
        except DomainError as exc:  # e.g. not found: expected, the next search reports it
            logger.info("fetch_case %s (%s): %s", gr_no, year, exc)


@dramatiq.actor(queue_name=LAWPHIL_QUEUE, time_limit=60 * _MINUTE, max_retries=1, min_backoff=_MINUTE)
def build_catalog(first_year: int) -> None:
    """One-time read of Lawphil's monthly lists (about 9 minutes). Always frees the lock when it ends."""
    _setup_logging()
    try:
        with SessionLocal() as session:
            report = Services(session).build_catalog().build(first_year)
        logger.info(
            "catalog build finished: %d read, %d skipped, %d decisions, %d missing, %d failed, %d broken",
            report.read, report.skipped, report.entries, len(report.missing), len(report.failed), len(report.broken),
        )
    finally:
        SqlJobLockRepository(engine).release(lock_keys.CATALOG_BUILD_KEY)


@dramatiq.actor(queue_name=LAWPHIL_QUEUE, time_limit=60 * _MINUTE, max_retries=1, min_backoff=_MINUTE)
def refresh_catalog() -> None:
    """Re-read the current and previous month (a few requests, at most once a day)."""
    _setup_logging()
    with SessionLocal() as session:
        report = Services(session).build_catalog().refresh()
    logger.info("catalog refresh: %d read, %d decisions", report.read, report.entries)


@dramatiq.actor(queue_name=DIGEST_QUEUE, time_limit=15 * _MINUTE, **_RETRIES)
def build_digest(digest_id: int, keys: list[str] | None = None) -> None:
    """Fill in a digest: the Court's text was stored when it was requested; this writes the AI answers one by one."""
    _setup_logging()
    try:
        with SessionLocal() as session:
            try:
                Services(session).build_case_digest().execute(digest_id, keys)
            except DomainError as exc:
                logger.info("build_digest %s: %s", digest_id, exc)
    finally:
        SqlJobLockRepository(engine).release(lock_keys.build_digest_key(digest_id, keys))
