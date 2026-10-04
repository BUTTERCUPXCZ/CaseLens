"""After a restart, start again the work that was running when the process stopped (only needed for the thread
queue: RabbitMQ keeps its own messages)."""
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from caselens.application.ports.gateways import JobQueue
from caselens.application.ports.locks import JobLockRepository
from caselens.domain.case_digest import DigestStatus
from caselens.infrastructure.db.orm_models import DigestModel, UploadModel
from caselens.infrastructure.db.session import SessionLocal

logger = logging.getLogger(__name__)

_RECENT = timedelta(days=7)


def requeue_unfinished_work(jobs: JobQueue, locks: JobLockRepository, session_factory=SessionLocal) -> tuple[int, int]:
    """Frees every old lock (nothing from before the restart is still running), then queues again each upload
    still "processing" and each digest still "pending" from the last 7 days. Returns (uploads, digests)."""
    locks.release_all()
    since = datetime.now(UTC) - _RECENT
    with session_factory() as session:
        upload_ids = list(
            session.scalars(
                select(UploadModel.id)
                .where(UploadModel.status == "processing", UploadModel.created_at >= since)
                .order_by(UploadModel.id)
            )
        )
        digest_ids = list(
            session.scalars(
                select(DigestModel.id)
                .where(DigestModel.status == DigestStatus.PENDING.value, DigestModel.created_at >= since)
                .order_by(DigestModel.id)
            )
        )
    for upload_id in upload_ids:
        jobs.enqueue_resolve_upload(upload_id)
    for digest_id in digest_ids:
        jobs.enqueue_build_digest(digest_id)
    logger.info("restart: queued %d unfinished upload(s) and %d pending digest(s)", len(upload_ids), len(digest_ids))
    return len(upload_ids), len(digest_ids)
