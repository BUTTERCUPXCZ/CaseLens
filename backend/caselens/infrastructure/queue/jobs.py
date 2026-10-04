"""The background jobs as plain functions. Two things run them: Dramatiq actors (RabbitMQ, see `actors.py`) and
the thread queue (`thread_job_queue.py`, for a host that has no separate workers). Each job builds its own
services and database session, and is safe to run twice (ingesting a stored case is ignored, a catalog build
carries on where it stopped, a digest only fills the answers still pending).
"""
import logging

from caselens.composition import Services
from caselens.domain.errors import DomainError
from caselens.domain.value_objects import GrNumber
from caselens.infrastructure.db.job_lock_repository import SqlJobLockRepository
from caselens.infrastructure.db.session import SessionLocal, engine
from caselens.infrastructure.queue import lock_keys

logger = logging.getLogger(__name__)


def resolve_upload(upload_id: int) -> None:
    with SessionLocal() as session:
        Services(session).resolve_upload_citations().execute(upload_id)


def fetch_case(gr_no: str, year: int | None) -> None:
    with SessionLocal() as session:
        try:
            Services(session).fetch_case_by_gr_number().execute(GrNumber(gr_no), year)
        except DomainError as exc:  # e.g. not found: expected, the next search reports it
            logger.info("fetch_case %s (%s): %s", gr_no, year, exc)


def build_catalog(first_year: int) -> None:
    """One-time read of Lawphil's monthly lists (about 9 minutes). Always frees the lock when it ends."""
    try:
        with SessionLocal() as session:
            report = Services(session).build_catalog().build(first_year)
        logger.info(
            "catalog build finished: %d read, %d skipped, %d decisions, %d missing, %d failed, %d broken",
            report.read, report.skipped, report.entries, len(report.missing), len(report.failed), len(report.broken),
        )
    finally:
        SqlJobLockRepository(engine).release(lock_keys.CATALOG_BUILD_KEY)


def refresh_catalog() -> None:
    """Re-read the current and previous month (a few requests, at most once a day)."""
    with SessionLocal() as session:
        report = Services(session).build_catalog().refresh()
    logger.info("catalog refresh: %d read, %d decisions", report.read, report.entries)


def build_digest(digest_id: int, keys: list[str] | None = None) -> None:
    """Fill in a digest: the Court's text was stored when it was requested; this writes the AI answers."""
    try:
        with SessionLocal() as session:
            try:
                Services(session).build_case_digest().execute(digest_id, keys)
            except DomainError as exc:
                logger.info("build_digest %s: %s", digest_id, exc)
    finally:
        SqlJobLockRepository(engine).release(lock_keys.build_digest_key(digest_id, keys))
