"""Questions about a case (the AI assistant panel) on real PostgreSQL, with the writer and the checker scripted (no AI)."""
import pytest
from fastapi.testclient import TestClient

from caselens.composition import Services
from caselens.domain.digest import AnswerSentence
from caselens.infrastructure.db.repositories import SqlCaseRepository
from caselens.main import create_app
from caselens.presentation.dependencies import get_services
from tests.fakes import FakeJobQueue, ScriptedWriter, VerdictChecker
from tests.helpers import parse_digest_case

pytestmark = pytest.mark.db


@pytest.fixture
def jobs():
    return FakeJobQueue()


@pytest.fixture
def case(db_session):
    return SqlCaseRepository(db_session).add(parse_digest_case("gr_180046_2009.html"))


@pytest.fixture
def services(db_session, jobs, case):
    grant = next(i for i, line in enumerate(case.full_text.split("\n")) if "WHEREFORE, we GRANT the petition" in line)
    writer = ScriptedWriter([AnswerSentence("The Court granted the petition.", (f"P{grant}",))])
    return Services(db_session, jobs=jobs, answer_writer=writer, answer_checker=VerdictChecker())


@pytest.fixture
def client(services):
    app = create_app()
    app.dependency_overrides[get_services] = lambda: services
    return TestClient(app)


def test_a_question_is_answered_in_the_background_and_listed_in_its_review(client, services, jobs, case):
    batch = client.post("/bulk", json={"text": ""}).json()
    asked = client.post(f"/cases/{case.id}/questions", json={"question": "What did the Court decide?", "batch_id": batch["id"]})
    assert asked.status_code == 202 and asked.json()["state"] == "pending" and jobs.case_questions == [asked.json()["id"]]

    services.answer_case_question().execute(jobs.case_questions[0])  # the worker
    listed = client.get(f"/cases/{case.id}/questions", params={"batch_id": batch["id"]}).json()
    assert [q["state"] for q in listed] == ["ready"] and listed[0]["sentences"][0]["text"] == "The Court granted the petition."
    assert listed[0]["sentences"][0]["cites"][0].startswith("P")
    assert client.get(f"/cases/{case.id}/questions").json() == []  # questions outside that review are separate

    assert client.delete(f"/bulk/{batch['id']}").status_code == 204  # deleting the review removes its questions
    assert client.get(f"/cases/{case.id}/questions", params={"batch_id": batch["id"]}).json() == []


def test_an_empty_question_or_an_unknown_case_is_refused(client, case):
    assert client.post(f"/cases/{case.id}/questions", json={"question": ""}).status_code == 422
    assert client.post(f"/cases/{case.id}/questions", json={"question": "   "}).status_code == 400
    assert client.post("/cases/999999/questions", json={"question": "Why?"}).status_code == 404
