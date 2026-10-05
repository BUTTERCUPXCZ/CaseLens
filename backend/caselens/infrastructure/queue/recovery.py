"""After a restart, start again the work that was running when the process stopped (only needed for the thread
queue: RabbitMQ keeps its own messages)."""
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, update

from caselens.application.ports.gateways import JobQueue
from caselens.application.ports.locks import JobLockRepository
from caselens.application.use_cases.case_digest_v2 import OVER_LIMIT_MESSAGE, month_start
from caselens.domain.case_digest import DigestStatus
from caselens.infrastructure.db.orm_models import BulkItemModel, CaseDigestV2Model, CaseQuestionModel, DigestModel, UploadModel
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
        bulk_ids = list(session.scalars(select(BulkItemModel.id).where(BulkItemModel.status == "queued").order_by(BulkItemModel.id)))
        case_digest_ids = list(session.scalars(select(CaseDigestV2Model.id).where(CaseDigestV2Model.state == "pending").order_by(CaseDigestV2Model.id)))
        question_ids = list(session.scalars(select(CaseQuestionModel.id).where(CaseQuestionModel.state == "pending", CaseQuestionModel.created_at >= since).order_by(CaseQuestionModel.id)))
    requeue_over_limit_digests(jobs, session_factory=session_factory)
    for item_id in bulk_ids:  # a bulk upload picks up where it stopped
        jobs.enqueue_bulk_item(item_id)
    for digest_id in case_digest_ids:  # and so does a case digest that was being written
        jobs.enqueue_case_digest(digest_id)
    for question_id in question_ids:  # and a question still waiting for its answer
        jobs.enqueue_case_question(question_id)
    for upload_id in upload_ids:
        jobs.enqueue_resolve_upload(upload_id)
    for digest_id in digest_ids:
        jobs.enqueue_build_digest(digest_id)
    logger.info(
        "restart: queued %d unfinished upload(s), %d pending digest(s), %d bulk item(s), %d case digest(s)",
        len(upload_ids), len(digest_ids), len(bulk_ids), len(case_digest_ids),
    )
    return len(upload_ids), len(digest_ids)


def requeue_over_limit_digests(jobs: JobQueue, *, limit: int | None = None, session_factory=SessionLocal) -> int:
    """Case digests that stopped because the monthly limit was reached are started again, oldest first, as far as
    this month's limit now allows (a new month, or a raised limit). Each one counts for the month it is started in."""
    if limit is None:
        from caselens.infrastructure.config import get_settings

        limit = get_settings().case_digest_monthly_limit
    now = datetime.now(UTC)
    with session_factory() as session:
        used = session.scalar(select(func.count()).select_from(CaseDigestV2Model).where(CaseDigestV2Model.created_at >= month_start(now))) or 0
        room = max(limit - used, 0) if limit else 10**9
        if room == 0:
            return 0
        digest_ids = list(
            session.scalars(
                select(CaseDigestV2Model.id)
                .where(CaseDigestV2Model.state == "failed", CaseDigestV2Model.error == OVER_LIMIT_MESSAGE)
                .order_by(CaseDigestV2Model.id)
                .limit(room)
            )
        )
        if digest_ids:
            session.execute(
                update(CaseDigestV2Model)
                .where(CaseDigestV2Model.id.in_(digest_ids))
                .values(state="pending", error=None, created_at=now, updated_at=now)
            )
            session.commit()
    for digest_id in digest_ids:
        jobs.enqueue_case_digest(digest_id)
    if digest_ids:
        logger.info("monthly limit: started %d case digest(s) that were waiting", len(digest_ids))
    return len(digest_ids)
