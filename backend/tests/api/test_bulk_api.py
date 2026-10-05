"""Bulk on real PostgreSQL: paste numbers, send files, the worker resolves each, progress and the library show one row per case."""
import io

import docx
import pytest
from fastapi.testclient import TestClient

from caselens.composition import Services
from caselens.main import create_app
from caselens.presentation.dependencies import get_services
from tests.fakes import FakeJobQueue, FixtureCaseSource
from tests.helpers import OFFICIAL_URL, official_html

pytestmark = pytest.mark.db


def word_file(*lines: str) -> bytes:
    document = docx.Document()
    for line in lines:
        document.add_paragraph(line)
    out = io.BytesIO()
    document.save(out)
    return out.getvalue()


@pytest.fixture
def jobs():
    return FakeJobQueue()


@pytest.fixture
def services(db_session, jobs):
    source = FixtureCaseSource({OFFICIAL_URL: official_html()}, {"180046": [OFFICIAL_URL]})
    return Services(db_session, case_locator=source, case_fetcher=source, jobs=jobs)


@pytest.fixture
def client(services):
    app = create_app()
    app.dependency_overrides[get_services] = lambda: services
    return TestClient(app)


def work(services, jobs):
    """What the worker does: resolve each queued item, one by one."""
    while jobs.bulk_items:
        services.resolve_bulk_item().execute(jobs.bulk_items.pop(0))


def test_pasted_numbers_are_resolved_into_one_row_and_progress_says_how_each_ended(client, services, jobs):
    started = client.post("/bulk", json={"text": "180046\n999999\nbanana\nG.R. No. 180046"})
    assert started.status_code == 201
    batch = started.json()
    assert batch["counts"]["total"] == 4 and batch["counts"]["queued"] == 2 + 1 and batch["finished"] is False

    work(services, jobs)
    done = client.get(f"/bulk/{batch['id']}").json()
    assert done["finished"] is True
    assert {k: done["counts"][k] for k in ("found", "duplicate", "not_found", "unreadable", "queued")} == {"found": 1, "duplicate": 1, "not_found": 1, "unreadable": 1, "queued": 0}
    assert done["counts"]["digests_pending"] == 1  # the found case's digest is asked for


def test_the_items_say_what_became_of_each_and_name_the_main_case(client, services, jobs):
    batch = client.post("/bulk", json={"text": "180046\n999999\nbanana\n180046"}).json()
    work(services, jobs)
    items = client.get(f"/bulk/{batch['id']}/items").json()["items"]
    assert [(i["label"], i["status"]) for i in items] == [("180046", "found"), ("999999", "not_found"), ("banana", "unreadable"), ("180046", "duplicate")]
    found = items[0]
    assert found["case"]["gr_no"] == "180046" and found["case"]["name"].startswith("Review Center Association") and found["digest"] == "pending"
    assert items[1]["case"] is None and items[1]["digest"] is None and "not on Lawphil's list" in items[1]["message"] and "(1969)" in items[1]["message"]
    assert client.get(f"/bulk/{batch['id']}/items", params={"status": "duplicate"}).json()["total"] == 1


def test_the_library_lists_the_case_once_however_many_times_it_was_given(client, services, jobs):
    batch = client.post("/bulk", json={"text": "180046\n180046\n180046"}).json()
    work(services, jobs)
    library = client.get("/library/cases", params={"q": "180046"}).json()
    assert library["total"] == 1
    assert client.get(f"/bulk/{batch['id']}").json()["counts"]["found"] == 1


def test_a_decision_file_is_one_case_and_the_cases_it_cites_are_not_added(client, services, jobs):
    batch = client.post("/bulk", json={"text": ""}).json()
    caption = word_file("EN BANC", "G.R. No. 180046 April 2, 2009", "REVIEW CENTER ASSOCIATION v. ERMITA", "D E C I S I O N", "CARPIO, J.:",
                        "As held in Ople v. Torres, G.R. No. 127685, July 23, 1998, and G.R. No. 111111.")
    response = client.post(f"/bulk/{batch['id']}/files", files=[("files", ("ermita.docx", caption, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))])
    assert response.status_code == 202 and [(i["label"], i["gr_no"], i["status"]) for i in response.json()["items"]] == [("ermita.docx", "180046", "queued")]
    work(services, jobs)
    counts = client.get(f"/bulk/{batch['id']}").json()["counts"]
    assert counts["total"] == 1 and counts["found"] == 1  # not three


def test_a_file_that_is_not_a_decision_and_one_that_is_not_a_document_are_reported_not_guessed(client, services, jobs):
    batch = client.post("/bulk", json={}).json()
    notes = word_file("My reviewer notes", "See G.R. No. 12345 for the rule.")
    response = client.post(f"/bulk/{batch['id']}/files", files=[
        ("files", ("notes.docx", notes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
        ("files", ("photo.png", b"not a document", "image/png")),
    ])
    items = response.json()["items"]
    assert [(i["label"], i["status"]) for i in items] == [("notes.docx", "unreadable"), ("photo.png", "unreadable")]
    assert "could not find a case in this file" in items[0]["message"]
    assert jobs.bulk_items == []


def test_too_many_files_in_one_request_and_a_batch_that_does_not_exist(client):
    batch = client.post("/bulk", json={}).json()
    many = [("files", (f"{i}.docx", b"x", "application/octet-stream")) for i in range(11)]
    assert client.post(f"/bulk/{batch['id']}/files", files=many).status_code == 400
    assert client.post("/bulk/99999/files", files=[("files", ("a.docx", b"x", "application/octet-stream"))]).status_code == 404
    assert client.get("/bulk/99999").status_code == 404 and client.get("/bulk/99999/items").status_code == 404


def test_the_uploads_tags_and_scope_reach_every_case_and_its_digest(client, services, jobs):
    tags = {s["name"]: s["id"] for s in client.get("/library/subject-list").json()}
    started = client.post("/bulk", json={"text": "180046", "subject_ids": [tags["Remedial Law"], tags["Litigation"]], "topic_scope": "Board exams"}).json()
    assert [s["name"] for s in started["subjects"]] == ["Remedial Law", "Litigation"] and started["topic_scope"] == "Board exams"
    work(services, jobs)
    assert client.get("/library/cases", params={"subject_id": tags["Litigation"]}).json()["total"] == 1
    row = client.get("/library/cases", params={"batch_id": started["id"]}).json()["items"][0]
    digest = client.get(f"/cases/{row['id']}/case-digest", params={"scope": "board exams"}).json()
    assert digest["state"] == "pending" and digest["scope"] == "Board exams"  # the upload's scope was asked for
    assert client.get(f"/bulk/{started['id']}").json()["counts"]["digests_pending"] == 1
    assert client.post("/bulk", json={"text": "1", "subject_ids": [99999]}).status_code == 400


def test_my_reviews_lists_uploads_newest_first_with_their_labels_and_one_can_be_deleted(client, services, jobs):
    older = client.post("/bulk", json={"text": "180046"}).json()
    newer = client.post("/bulk", json={"text": "999999\nbanana"}).json()
    listed = client.get("/bulk", params={"limit": 2}).json()
    assert [b["id"] for b in listed] == [newer["id"], older["id"]] and listed[0]["labels"] == ["999999", "banana"]
    assert client.delete(f"/bulk/{newer['id']}").status_code == 204
    assert client.get(f"/bulk/{newer['id']}").status_code == 404 and client.delete(f"/bulk/{newer['id']}").status_code == 404


def test_retry_queues_the_failed_items_again_and_recent_batches_are_listed(client, services, jobs, db_session):
    from caselens.domain.bulk import ItemStatus
    from caselens.infrastructure.db.bulk_repository import SqlBulkRepository

    batch = client.post("/bulk", json={"text": "180046"}).json()
    repo = SqlBulkRepository(db_session)
    item = repo.get_item(jobs.bulk_items.pop())
    item.status, item.message = ItemStatus.FAILED, "Lawphil did not answer"
    repo.save_item(item)
    assert client.post(f"/bulk/{batch['id']}/retry").json() == {"requeued": 1}
    assert jobs.bulk_items == [item.id]
    assert [b["id"] for b in client.get("/bulk").json()][0] == batch["id"]


def test_the_results_of_an_upload_are_its_main_cases_once_each_with_the_state_of_their_digest(client, services, jobs):
    batch = client.post("/bulk", json={"text": "180046\nbanana\nG.R. No. 180046\n999999"}).json()
    assert client.get("/library/cases", params={"batch_id": batch["id"]}).json()["total"] == 0  # nothing resolved yet

    work(services, jobs)
    page = client.get("/library/cases", params={"batch_id": batch["id"]}).json()

    assert page["total"] == 1 and len(page["items"]) == 1  # the repeat, the junk line and the unknown number are not rows
    row = page["items"][0]
    assert row["gr_no"] == "180046" and row["digest_state"] == "pending" and row["digest_ready"] is False
    other = client.post("/bulk", json={"text": "999999"}).json()
    assert client.get("/library/cases", params={"batch_id": other["id"]}).json()["total"] == 0


def test_a_digest_file_whose_citation_puts_the_reporter_first_finds_its_case_and_keeps_the_scra_line(client, services, jobs):
    # The shape of the client's own sample (Marcos_v_Manglapus_Case_Digest.docx), with a case this test can fetch.
    batch = client.post("/bulk", json={"text": ""}).json()
    sample = word_file("CASE DIGEST", "Review Center v. Ermita", "583 SCRA 428, G.R. No. 180046, April 2, 2009 (En Banc)", "Topic: Constitutional Law")
    items = client.post(f"/bulk/{batch['id']}/files", files=[("files", ("digest.docx", sample, "application/octet-stream"))]).json()["items"]
    assert items[0]["status"] == "queued" and items[0]["gr_no"] == "180046"
    work(services, jobs)
    case_id = client.get("/library/cases", params={"batch_id": batch["id"]}).json()["items"][0]["id"]
    header = client.get(f"/cases/{case_id}/case-digest", params={"batch_id": batch["id"]}).json()["header"]
    assert header["citation"].startswith("583 SCRA 428, G.R. No. 180046")
    assert not client.get(f"/cases/{case_id}/case-digest").json()["header"]["citation"].startswith("583 SCRA")  # only in that review


def test_the_clients_reviewer_pdf_becomes_the_case_in_its_digest_boxes(client, services, jobs):
    from tests.helpers import FIXTURES

    batch = client.post("/bulk", json={"text": ""}).json()
    pdf = (FIXTURES / "sample_case.pdf").read_bytes()
    items = client.post(f"/bulk/{batch['id']}/files", files=[("files", ("sample case.pdf", pdf, "application/pdf"))]).json()["items"]
    assert [(i["label"], i["gr_no"], i["status"]) for i in items] == [("sample case.pdf: Review Center v Ermita", "180046", "queued")]
    work(services, jobs)
    rows = client.get("/library/cases", params={"batch_id": batch["id"]}).json()["items"]
    assert [r["gr_no"] for r in rows] == ["180046"]
    header = client.get(f"/cases/{rows[0]['id']}/case-digest", params={"batch_id": batch["id"]}).json()["header"]
    assert header["citation"].startswith("538 SCRA 428, G.R. No. 180046, April 2, 2009")  # the Court's date, not the 2010 the notes wrote


def test_an_individual_upload_is_one_case_and_says_so(client, services, jobs):
    one = client.post("/bulk", json={"text": "180046", "kind": "individual"}).json()
    assert one["kind"] == "individual" and one["counts"]["total"] == 1
    assert client.post("/bulk", json={"text": "180046\n173931", "kind": "individual"}).status_code == 400  # two cases: that is Bulk
    empty = client.post("/bulk", json={"text": "", "kind": "individual"}).json()
    two_files = [("files", (f"case{i}.docx", word_file("G.R. No. 180046, April 2, 2009"), "application/octet-stream")) for i in range(2)]
    assert client.post(f"/bulk/{empty['id']}/files", files=two_files).status_code == 400
    assert client.post("/bulk", json={"text": "1"}).json()["kind"] == "bulk"  # the default
    assert client.post("/bulk", json={"text": "1", "kind": "other"}).status_code == 422


def test_my_uploads_names_the_cases_each_upload_gave(client, services, jobs):
    batch = client.post("/bulk", json={"text": "180046\nbanana"}).json()
    assert client.get(f"/bulk/{batch['id']}").json()["cases"] == []  # nothing found yet
    work(services, jobs)
    listed = next(b for b in client.get("/bulk").json() if b["id"] == batch["id"])
    assert listed["case_total"] == 1 and listed["cases"][0]["gr_no"] == "180046"
    assert listed["cases"][0]["name"].startswith("Review Center Association of the Philippines")
