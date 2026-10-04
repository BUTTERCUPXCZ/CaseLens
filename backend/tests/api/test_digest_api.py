"""The digest endpoints on real PostgreSQL, with real decisions. The AI is a scripted fake: the real Gemini calls are
measured separately (tests/eval/)."""
import pytest
from fastapi.testclient import TestClient

from caselens.composition import Services
from caselens.domain.digest import AnswerSentence
from caselens.domain.entities import Upload
from caselens.infrastructure.db.repositories import SqlCaseRepository, SqlUploadRepository
from caselens.main import create_app
from caselens.presentation.dependencies import get_services
from tests.fakes import AlwaysSupported, FakeJobQueue, ScriptedWriter
from tests.helpers import parse_digest_case

pytestmark = pytest.mark.db


@pytest.fixture
def jobs():
    return FakeJobQueue()


@pytest.fixture
def writer():
    return ScriptedWriter([AnswerSentence("The Court declared the order void.", ("P132",))])


@pytest.fixture
def services(db_session, jobs, writer):
    return Services(db_session, jobs=jobs, answer_writer=writer, answer_checker=AlwaysSupported())


@pytest.fixture
def client(services):
    app = create_app()
    app.dependency_overrides[get_services] = lambda: services
    return TestClient(app)


@pytest.fixture
def case_id(db_session):
    return SqlCaseRepository(db_session).add(parse_digest_case("gr_180046_2009.html")).id


def field(body, key):
    return next(f for f in body["fields"] if f["key"] == key)


def test_requesting_a_digest_returns_the_courts_text_at_once_and_queues_the_answers(client, case_id, jobs):
    response = client.post(f"/cases/{case_id}/digest", json={})

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "pending" and body["gr_no"] == "180046" and body["source_url"].endswith("gr_180046_2009.html")
    assert field(body, "ruling")["text"].startswith("WHEREFORE, we GRANT the petition")
    assert field(body, "ruling")["origin"] == "court_ruling"
    assert field(body, "facts")["passage"] == {"first": 9, "last": 12}
    assert field(body, "doctrine")["origin"] == "empty" and "do not guess" in field(body, "doctrine")["note"]
    assert field(body, "topic")["state"] == "pending"
    assert (body["pickable_first"], body["pickable_last"]) == (6, 132)
    assert "Lawphil" in body["attribution"]["source"]
    assert jobs.digest_builds == [(body["id"], None)]


def test_after_the_worker_runs_the_answers_are_there_with_their_sources(client, case_id, services):
    digest_id = client.post(f"/cases/{case_id}/digest", json={}).json()["id"]
    services.build_case_digest().execute(digest_id)

    body = client.get(f"/digests/{digest_id}").json()
    assert body["status"] == "ready"
    topic = field(body, "topic")
    assert (topic["state"], topic["origin"], topic["cites"]) == ("ready", "ai_drafted", ["P132"])
    assert topic["text"] == "The Court declared the order void."


def test_without_an_ai_key_the_digest_is_still_useful(db_session, case_id):
    services = Services(db_session, jobs=FakeJobQueue(), ai_enabled=False)
    app = create_app()
    app.dependency_overrides[get_services] = lambda: services
    client = TestClient(app)

    digest_id = client.post(f"/cases/{case_id}/digest", json={}).json()["id"]
    services.build_case_digest().execute(digest_id)
    body = client.get(f"/digests/{digest_id}").json()
    assert field(body, "topic")["state"] == "unavailable"
    assert field(body, "topic")["note"] == "Written explanations are not set up on this server."
    assert field(body, "ruling")["text"] and body["status"] == "ready"


def test_asking_for_the_same_digest_again_returns_it_and_does_not_queue_twice(client, case_id, jobs):
    first = client.post(f"/cases/{case_id}/digest", json={}).json()["id"]
    second = client.post(f"/cases/{case_id}/digest", json={})
    assert second.json()["id"] == first and len(jobs.digest_builds) == 1
    assert client.get(f"/cases/{case_id}/digest").json()["id"] == first


def test_the_short_template_is_ready_at_once(client, case_id):
    response = client.post(f"/cases/{case_id}/digest", json={"template": "facts_and_doctrine"})
    assert response.status_code == 200
    assert [f["key"] for f in response.json()["fields"]] == ["facts", "doctrine"]


def test_editing_a_field_then_resetting_it(client, case_id):
    digest_id = client.post(f"/cases/{case_id}/digest", json={}).json()["id"]

    edited = client.put(f"/digests/{digest_id}/fields/ruling/text", json={"text": "Mine."}).json()
    assert (field(edited, "ruling")["text"], field(edited, "ruling")["origin"], field(edited, "ruling")["edited"]) == ("Mine.", "student_written", True)
    assert field(edited, "ruling")["can_reset"] is True

    restored = client.post(f"/digests/{digest_id}/fields/ruling/reset").json()
    assert field(restored, "ruling")["origin"] == "court_ruling" and not field(restored, "ruling")["edited"]


def test_picking_paragraphs_gives_the_courts_exact_words(client, case_id, db_session):
    digest_id = client.post(f"/cases/{case_id}/digest", json={}).json()["id"]
    body = client.put(f"/digests/{digest_id}/fields/doctrine/passage", json={"first": 109, "last": 109}).json()

    doctrine = field(body, "doctrine")
    stored = SqlCaseRepository(db_session).get(case_id).full_text.split("\n")[109]
    assert doctrine["text"] == stored and doctrine["origin"] == "student_picked"
    assert doctrine["passage"] == {"first": 109, "last": 109}


def test_pasting_marks_the_text_as_pasted(client, case_id):
    digest_id = client.post(f"/cases/{case_id}/digest", json={}).json()["id"]
    body = client.post(f"/digests/{digest_id}/fields/doctrine/paste", json={"text": "Pasted rule."}).json()
    assert field(body, "doctrine")["origin"] == "student_pasted"


@pytest.mark.parametrize(("first", "last"), [(0, 3), (10, 5), (9, 60), (130, 140)])
def test_a_bad_passage_is_refused_in_plain_words(client, case_id, first, last):
    digest_id = client.post(f"/cases/{case_id}/digest", json={}).json()["id"]
    response = client.put(f"/digests/{digest_id}/fields/doctrine/passage", json={"first": first, "last": last})
    assert response.status_code == 422 and response.json()["detail"]


def test_a_student_question_is_added_and_queued(client, case_id, jobs):
    digest_id = client.post(f"/cases/{case_id}/digest", json={}).json()["id"]
    response = client.post(f"/digests/{digest_id}/questions", json={"question": "Is EO 566 valid?"})
    assert response.status_code == 202
    added = field(response.json(), "q1")
    assert (added["label"], added["state"], added["kind"]) == ("Is EO 566 valid?", "pending", "answer")
    assert jobs.digest_builds[-1] == (digest_id, ["q1"])


def test_only_answer_fields_can_be_regenerated(client, case_id):
    digest_id = client.post(f"/cases/{case_id}/digest", json={}).json()["id"]
    assert client.post(f"/digests/{digest_id}/regenerate", json={"keys": ["why"]}).status_code == 202
    assert client.post(f"/digests/{digest_id}/regenerate", json={"keys": ["ruling"]}).status_code == 422


def test_the_digests_of_a_review_are_listed_together(client, case_id, db_session):
    upload = SqlUploadRepository(db_session).add(Upload(filename="reviewer.pdf", text="x"))
    mine = client.post(f"/cases/{case_id}/digest", json={"upload_id": upload.id}).json()["id"]
    client.post(f"/cases/{case_id}/digest", json={})  # the stand-alone one is not in the review's list
    listed = client.get(f"/uploads/{upload.id}/digests").json()
    assert [d["id"] for d in listed] == [mine]


def test_unknown_things_are_404(client, case_id):
    assert client.get("/digests/999999").status_code == 404
    assert client.get(f"/cases/{case_id}/digest").status_code == 404  # none requested yet
    assert client.post("/cases/999999/digest", json={}).status_code == 404
    assert client.put("/digests/999999/fields/facts/text", json={"text": "x"}).status_code == 404


def test_an_unknown_field_is_refused(client, case_id):
    digest_id = client.post(f"/cases/{case_id}/digest", json={}).json()["id"]
    assert client.put(f"/digests/{digest_id}/fields/nonsense/text", json={"text": "x"}).status_code == 422
