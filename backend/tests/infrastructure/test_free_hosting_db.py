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


def test_a_restart_picks_up_queued_bulk_items_and_case_digests_that_were_being_written(db_session):
    from caselens.domain.bulk import BulkBatch, BulkItem, ItemKind, ItemStatus
    from caselens.domain.digest_v2 import CaseDigestV2, DigestState
    from caselens.infrastructure.db.bulk_repository import SqlBulkRepository
    from caselens.infrastructure.db.case_digest_repository import SqlCaseDigestRepository
    from caselens.infrastructure.db.repositories import SqlCaseRepository
    from tests.helpers import parse_digest_case

    case = SqlCaseRepository(db_session).add(parse_digest_case("gr_180046_2009.html"))
    pending = SqlCaseDigestRepository(db_session).save(CaseDigestV2(case_id=case.id, state=DigestState.PENDING))
    bulk = SqlBulkRepository(db_session)
    batch = bulk.add_batch(BulkBatch(items=[
        BulkItem(0, 0, ItemKind.GR_NUMBER, "1111", "1111"),
        BulkItem(0, 0, ItemKind.GR_NUMBER, "2222", "2222", status=ItemStatus.FOUND),  # settled: not queued again
    ]))
    jobs = FakeJobQueue()

    requeue_unfinished_work(jobs, InMemoryJobLocks(), session_factory=lambda: nullcontext(db_session))

    assert jobs.bulk_items == [batch.items[0].id] and pending.id in jobs.case_digests


def test_digests_that_waited_for_the_monthly_limit_start_again_as_far_as_the_limit_allows(db_session):
    from caselens.application.use_cases.case_digest_v2 import OVER_LIMIT_MESSAGE
    from caselens.domain.digest_v2 import CaseDigestV2, DigestState
    from caselens.infrastructure.db.case_digest_repository import SqlCaseDigestRepository
    from caselens.infrastructure.db.repositories import SqlCaseRepository
    from caselens.infrastructure.queue.recovery import requeue_over_limit_digests
    from tests.helpers import parse_digest_case

    case = SqlCaseRepository(db_session).add(parse_digest_case("gr_180046_2009.html"))
    waiting = SqlCaseDigestRepository(db_session).save(CaseDigestV2(case_id=case.id, state=DigestState.FAILED, error=OVER_LIMIT_MESSAGE))
    factory = lambda: nullcontext(db_session)  # noqa: E731

    full = FakeJobQueue()
    assert requeue_over_limit_digests(full, limit=1, session_factory=factory) == 0  # this month's one is used up: it waits
    assert full.case_digests == []

    jobs = FakeJobQueue()
    assert requeue_over_limit_digests(jobs, limit=5, session_factory=factory) == 1  # limit raised: it starts
    assert jobs.case_digests == [waiting.id]
    assert SqlCaseDigestRepository(db_session).get(case.id).state is DigestState.PENDING


def test_migration_0013_goes_down_and_up_again_keeping_the_tags(test_engine):
    """The tags migration can be undone (one tag per case comes back) and redone, on a copy of the test schema."""
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import text

    from tests.conftest import BACKEND_DIR

    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    with test_engine.begin() as connection:
        config.attributes["connection"] = connection
        case_id = connection.execute(text(
            "INSERT INTO cases (gr_no, title, doc_type, disposition, source_url, raw_html, full_text, parser_version) "
            "VALUES ('1', 't', 'decision', 'unknown', 'https://lawphil.net/x-0013', '', '', 1) RETURNING id"
        )).scalar()
        civil = connection.execute(text("SELECT id FROM subjects WHERE name = 'Civil Law'")).scalar()
        connection.execute(text("INSERT INTO case_subjects (case_id, subject_id) VALUES (:c, :s)"), {"c": case_id, "s": civil})
        command.downgrade(config, "0012")
        assert connection.execute(text("SELECT subject_id FROM cases WHERE id = :c"), {"c": case_id}).scalar() == civil
        command.upgrade(config, "head")
        assert connection.execute(text("SELECT subject_id FROM case_subjects WHERE case_id = :c"), {"c": case_id}).scalar() == civil
        connection.execute(text("DELETE FROM cases WHERE id = :c"), {"c": case_id})
