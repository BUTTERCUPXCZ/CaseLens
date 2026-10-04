"""On real PostgreSQL: RLS is on for every table (migration 0009), old uploads are deleted, unfinished work is queued again."""
from contextlib import nullcontext
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text

from caselens.infrastructure.db.orm_models import DigestModel, UploadModel
from caselens.infrastructure.db.upload_cleanup import delete_old_uploads
from caselens.infrastructure.queue.recovery import requeue_unfinished_work
from tests.fakes import FakeJobQueue, InMemoryJobLocks

pytestmark = pytest.mark.db


def test_every_table_has_row_level_security_on(db_session):
    off = db_session.execute(
        text("SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND NOT rowsecurity")
    ).scalars().all()
    assert off == []


def add_upload(session, status: str, age_days: int) -> UploadModel:
    row = UploadModel(filename="r.pdf", text="x", status=status, created_at=datetime.now(UTC) - timedelta(days=age_days))
    session.add(row)
    session.flush()
    return row


def test_uploads_older_than_the_limit_are_deleted_and_newer_ones_stay(db_session):
    old = add_upload(db_session, "done", 10)
    new = add_upload(db_session, "done", 2)
    assert delete_old_uploads(db_session, keep_days=7) >= 1
    db_session.expire_all()
    assert db_session.get(UploadModel, old.id) is None
    assert db_session.get(UploadModel, new.id) is not None


def test_a_restart_queues_processing_uploads_again_and_frees_old_locks(db_session):
    processing = add_upload(db_session, "processing", 1)
    add_upload(db_session, "done", 1)
    add_upload(db_session, "processing", 30)  # too old to bother with
    locks = InMemoryJobLocks()
    locks.acquire("caselens:build-digest:1:all", 60)
    jobs = FakeJobQueue()

    uploads, _ = requeue_unfinished_work(jobs, locks, session_factory=lambda: nullcontext(db_session))

    assert processing.id in jobs.resolve_upload_ids
    assert uploads == len(jobs.resolve_upload_ids)
    assert locks.held == set()
