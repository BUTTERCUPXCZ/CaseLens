"""The desktop app runs 12 digests at once on one SQLite file. A digest waits minutes for the AI while other jobs save; its own
save at the end must still go through (SQLite refuses a write from a read that was held open while others wrote)."""
from sqlalchemy.orm import sessionmaker

from caselens.composition import Services
from caselens.domain.digest_v2 import CaseDigestV2, DigestState
from caselens.infrastructure.db.case_digest_repository import SqlCaseDigestRepository
from caselens.infrastructure.db.repositories import SqlCaseRepository
from caselens.infrastructure.db.session import make_engine
from caselens.infrastructure.db.sqlite_schema import upgrade_sqlite
from tests.api.test_case_digest_api import DRAFT
from tests.fakes import FakeJobQueue, ScriptedDigestWriter, VerdictChecker
from tests.helpers import parse_digest_case


class WriterWhileOthersSave(ScriptedDigestWriter):
    """While "the AI" works on this digest, another job saves its own digest."""

    def __init__(self, draft, other_job):
        super().__init__(draft)
        self.other_job = other_job

    def write(self, request):
        self.other_job()
        return super().write(request)


def test_a_digest_is_saved_even_though_other_jobs_saved_while_it_waited_for_the_ai(tmp_path):
    url = f"sqlite:///{(tmp_path / 'caselens.db').as_posix()}"
    upgrade_sqlite(url)
    engine = make_engine(url)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    with Session() as setup:
        case_id = SqlCaseRepository(setup).add(parse_digest_case("gr_180046_2009.html")).id
        mine = SqlCaseDigestRepository(setup).save(CaseDigestV2(case_id, "")).id
        other = SqlCaseDigestRepository(setup).save(CaseDigestV2(case_id, "Delegation")).id
        setup.commit()

    def other_job():
        with Session() as session:
            digests = SqlCaseDigestRepository(session)
            done = digests.get_by_id(other)
            done.state = DigestState.FAILED
            digests.save(done)
            session.commit()

    with Session() as session:
        writer = WriterWhileOthersSave(DRAFT, other_job)
        result = Services(session, jobs=FakeJobQueue(), digest_writer=writer, answer_checker=VerdictChecker()).build_case_digest_v2().execute(mine)

    assert result.state is DigestState.READY
    with Session() as session:
        assert SqlCaseDigestRepository(session).get_by_id(mine).state is DigestState.READY
    engine.dispose()
