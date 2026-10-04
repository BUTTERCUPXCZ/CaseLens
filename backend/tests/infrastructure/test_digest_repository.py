"""The digest table on real PostgreSQL (built by migration 0006)."""
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from caselens.application.use_cases.request_case_digest import RequestCaseDigest
from caselens.domain.case_digest import CaseDigest, DigestStatus, DigestTemplate, FieldOrigin, Passage
from caselens.domain.services.digest_field_factory import DigestFieldFactory
from caselens.infrastructure.db.digest_repository import SqlDigestRepository
from caselens.infrastructure.db.repositories import SqlCaseRepository, SqlUnitOfWork
from tests.fakes import FakeJobQueue
from tests.helpers import parse_digest_case

pytestmark = pytest.mark.db


@pytest.fixture
def case(db_session):
    return SqlCaseRepository(db_session).add(parse_digest_case("gr_180046_2009.html"))


@pytest.fixture
def repo(db_session):
    return SqlDigestRepository(db_session)


def new_digest(case, upload_id=None):
    return CaseDigest(
        case_id=case.id, upload_id=upload_id, template=DigestTemplate.FULL,
        fields=DigestFieldFactory().build(DigestTemplate.FULL, case.full_text), parser_version=case.parser_version,
    )


def test_a_digest_round_trips_with_every_field_and_the_original_of_an_edit(repo, case):
    stored = repo.add(new_digest(case))
    ruling = stored.field_named("ruling")
    stored.replace_field(ruling.edited_to("My words", FieldOrigin.STUDENT_WRITTEN))
    repo.save(stored)

    loaded = repo.get(stored.id)
    again = loaded.field_named("ruling")
    assert (again.text, again.origin, again.edited) == ("My words", FieldOrigin.STUDENT_WRITTEN, True)
    assert again.original.text.startswith("WHEREFORE, we GRANT the petition")
    assert loaded.field_named("facts").passage == Passage(9, 12)
    assert [f.key for f in loaded.fields] == ["facts", "issues", "ruling", "doctrine", "topic", "why"]
    assert loaded.status is DigestStatus.PENDING and loaded.created_at is not None


def test_one_digest_per_case_per_review_and_one_stand_alone_per_case(repo, case, db_session):
    repo.add(new_digest(case, upload_id=None))
    with pytest.raises(IntegrityError):
        repo.add(new_digest(case, upload_id=None))  # NULL upload_id still counts as one slot


def test_find_tells_a_review_digest_from_the_stand_alone_one(repo, case, db_session):
    from caselens.domain.entities import Upload
    from caselens.infrastructure.db.repositories import SqlUploadRepository

    upload = SqlUploadRepository(db_session).add(Upload(filename="r.pdf", text="x"))
    alone, inside = repo.add(new_digest(case)), repo.add(new_digest(case, upload_id=upload.id))
    assert repo.find(case.id, None).id == alone.id
    assert repo.find(case.id, upload.id).id == inside.id
    assert [d.id for d in repo.list_for_upload(upload.id)] == [inside.id]
    assert repo.find(case.id, 99999) is None and repo.get(99999) is None


def test_the_daily_ai_count_counts_only_digests_answered_since_the_time(repo, case):
    stored = repo.add(new_digest(case))
    now = datetime.now(UTC)
    assert repo.count_ai_since(now - timedelta(days=1)) == 0
    stored.ai_answered_at = now
    repo.save(stored)
    assert repo.count_ai_since(now - timedelta(days=1)) == 1
    assert repo.count_ai_since(now + timedelta(days=1)) == 0


def test_deleting_the_case_removes_its_digests(repo, case, db_session):
    stored = repo.add(new_digest(case))
    db_session.delete(db_session.get(__import__("caselens.infrastructure.db.orm_models", fromlist=["CaseModel"]).CaseModel, case.id))
    db_session.flush()
    assert repo.get(stored.id) is None


def test_requesting_through_the_real_repositories_stores_the_courts_text_at_once(db_session, case):
    jobs = FakeJobQueue()
    request = RequestCaseDigest(SqlCaseRepository(db_session), SqlDigestRepository(db_session), jobs, SqlUnitOfWork(db_session))
    digest = request.execute(case.id)
    assert digest.id and digest.field_named("ruling").text.startswith("WHEREFORE")
    assert jobs.digest_builds == [(digest.id, None)]
