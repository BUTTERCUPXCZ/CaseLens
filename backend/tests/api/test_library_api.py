"""The library on real PostgreSQL: one row per main case, subjects with counts, the filter, and the subject setting."""
import pytest
from fastapi.testclient import TestClient

from caselens.composition import Services
from caselens.infrastructure.db.repositories import SqlCaseRepository
from caselens.main import create_app
from caselens.presentation.dependencies import get_services
from tests.helpers import parse_digest_case

pytestmark = pytest.mark.db


@pytest.fixture
def client(db_session) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_services] = lambda: Services(db_session)
    return TestClient(app)


@pytest.fixture
def cases(db_session):
    repo = SqlCaseRepository(db_session)
    first = repo.add(parse_digest_case("gr_180046_2009.html"))
    second = repo.add(parse_digest_case("gr_173931_2009.html"))
    return repo, first, second


def tag_ids(client, *names):
    by_name = {s["name"]: s["id"] for s in client.get("/library/subject-list").json()}
    return [by_name[n] for n in names]


def test_the_tags_are_the_clients_list_in_the_order_of_his_screen(client):
    names = [s["name"] for s in client.get("/library/subject-list").json()]
    assert names == [
        "Civil Law", "Criminal Law", "Remedial Law", "Constitutional Law", "Labor Law", "Commercial Law",
        "Taxation Law", "Legal Ethics", "Political Law", "Litigation", "Administrative Law",
    ]


def test_the_rail_counts_a_case_under_each_of_its_tags_and_the_ones_with_none(client, cases):
    _, first, _ = cases
    before = {r["name"]: r for r in client.get("/library/subjects").json()}
    assert before["No subject yet"]["count"] >= 2 and before["No subject yet"]["subject_id"] is None
    tagged = client.put(f"/cases/{first.id}/subjects", json={"subject_ids": tag_ids(client, "Political Law", "Constitutional Law")}).json()
    assert [s["name"] for s in tagged["subjects"]] == ["Constitutional Law", "Political Law"]  # in the list's order
    after = {r["name"]: r["count"] for r in client.get("/library/subjects").json()}
    assert after["Constitutional Law"] == 1 and after["Political Law"] == 1 and after["No subject yet"] == before["No subject yet"]["count"] - 1


def test_the_library_filters_by_tag(client, cases):
    _, first, second = cases
    [law] = tag_ids(client, "Constitutional Law")
    client.put(f"/cases/{first.id}/subjects", json={"subject_ids": [law]})
    listed = client.get("/library/cases", params={"subject_id": law}).json()
    assert [c["id"] for c in listed["items"]] == [first.id] and listed["items"][0]["subjects"] == [{"id": law, "name": "Constitutional Law"}]
    none_yet = client.get("/library/cases", params={"no_subject": True}).json()
    assert second.id in [c["id"] for c in none_yet["items"]] and first.id not in [c["id"] for c in none_yet["items"]]


def test_a_related_page_is_stored_but_not_listed(client, cases, db_session):
    repo, first, second = cases
    repo.set_main_case([second.id], first.id)  # the second page is only a related page of the first
    ids = [c["id"] for c in client.get("/library/cases").json()["items"]]
    assert first.id in ids and second.id not in ids
    assert client.get(f"/cases/{second.id}").status_code == 200  # its text is still there, one click away


def test_the_listing_says_every_number_the_decision_settles(client, db_session):
    SqlCaseRepository(db_session).add(parse_digest_case("gr_148263_2009.html"))
    row = next(c for c in client.get("/library/cases", params={"q": "David"}).json()["items"] if c["gr_no"] == "148263")
    assert row["numbers"] == ["148263", "148271", "148272"]


def test_clearing_the_tags_and_refusing_one_that_does_not_exist(client, cases):
    _, first, _ = cases
    client.put(f"/cases/{first.id}/subjects", json={"subject_ids": tag_ids(client, "Remedial Law")})
    assert client.put(f"/cases/{first.id}/subjects", json={"subject_ids": []}).json()["subjects"] == []
    assert client.put(f"/cases/{first.id}/subjects", json={"subject_ids": [99999]}).status_code == 400
    assert client.put("/cases/999999/subjects", json={"subject_ids": tag_ids(client, "Remedial Law")}).status_code == 404


def test_the_listing_says_which_cases_already_have_a_digest(client, cases, db_session):
    from caselens.domain.digest_v2 import CaseDigestV2, DigestState
    from caselens.infrastructure.db.case_digest_repository import SqlCaseDigestRepository

    _, first, second = cases
    SqlCaseDigestRepository(db_session).save(CaseDigestV2(case_id=first.id, state=DigestState.READY))
    SqlCaseDigestRepository(db_session).save(CaseDigestV2(case_id=second.id, state=DigestState.PENDING))  # being written: not ready
    ready = {c["id"]: c["digest_ready"] for c in client.get("/library/cases").json()["items"] if c["id"] in (first.id, second.id)}
    assert ready == {first.id: True, second.id: False}
