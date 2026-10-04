"""The catalog endpoints on real PostgreSQL, loaded from REAL parsed Lawphil months."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from caselens.composition import Services
from caselens.domain.entities import IndexPage
from caselens.domain.value_objects import GrNumber
from caselens.infrastructure.db.catalog_repository import SqlCatalogRepository
from caselens.infrastructure.lawphil.catalog_parser import LawphilCatalogParser
from caselens.infrastructure.lawphil.html_decoding import decode_html
from caselens.main import create_app
from caselens.presentation.dependencies import get_services
from tests.fakes import FakeJobQueue, FixtureCaseSource
from tests.helpers import OFFICIAL_URL, official_html

pytestmark = pytest.mark.db

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "catalog"


@pytest.fixture
def jobs() -> FakeJobQueue:
    return FakeJobQueue()


@pytest.fixture
def running() -> dict:
    return {"build": False}


@pytest.fixture
def services(db_session, jobs, running) -> Services:
    source = FixtureCaseSource({OFFICIAL_URL: official_html()}, {"180046": [OFFICIAL_URL]})
    return Services(db_session, case_locator=source, case_fetcher=source, jobs=jobs, build_probe=lambda: running["build"])


@pytest.fixture
def client(services) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_services] = lambda: services
    return TestClient(app)


@pytest.fixture
def loaded(db_session):
    """April 2009 and July 2015, as read from Lawphil."""
    repo = SqlCatalogRepository(db_session)
    for name, year, month, code in [("apr2009.html", 2009, 4, "apr"), ("jul2015.html", 2015, 7, "jul")]:
        page = IndexPage(year, month, f"https://lawphil.net/judjuris/juri{year}/{code}{year}/{code}{year}.html")
        parsed = LawphilCatalogParser().parse(decode_html((FIXTURES / name).read_bytes(), "text/html"), page.url)
        repo.register_months([page])
        repo.replace_month(page, parsed.entries)


def test_search_by_case_name_finds_the_real_case(client, loaded, jobs):
    body = client.get("/catalog/search", params={"q": "review center ermita"}).json()

    assert body["understood_as"] == "name" and body["total"] == 1
    item = body["items"][0]
    assert (item["gr_no"], item["numbers"], item["decision_date"], item["in_library"], item["case_id"]) == (
        "180046", ["180046"], "2009-04-02", False, None,
    )
    # exactly as Lawphil's own list prints it, typos included ("Associations", "Secretatry"):
    assert item["title"] == "Review Center Associations of the Philippines vs. Executive Secretatry Eduardo Ermita, et al."
    assert item["source_url"] == OFFICIAL_URL
    assert "lawphil.net" in body["attribution"]["source"]


@pytest.mark.parametrize("typed", ["180046", "G.R. No. 180046", "gr no 180046"])
def test_search_by_number_however_it_is_typed(client, loaded, typed):
    body = client.get("/catalog/search", params={"q": typed}).json()
    assert body["understood_as"] == "number" and [i["gr_no"] for i in body["items"]] == ["180046"]


def test_a_joint_decision_is_found_by_either_number_and_says_what_it_was_decided_with(client, loaded):
    for number in ("211972", "212045"):
        (item,) = client.get("/catalog/search", params={"q": number}).json()["items"]
        assert (item["gr_no"], item["numbers"], item["also_decided_with"]) == ("211972", ["211972", "212045"], ["212045"])


def test_a_saved_case_is_marked_as_in_the_library(client, loaded, services):
    services.fetch_case_by_gr_number().execute(GrNumber("180046"), 2009)

    (item,) = client.get("/catalog/search", params={"q": "180046"}).json()["items"]

    assert item["in_library"] is True and item["case_id"] is not None


def test_the_year_narrows_and_paging_reports_the_total(client, loaded):
    everything = client.get("/catalog/search", params={"q": "people", "limit": 5}).json()
    assert everything["total"] > 5 and len(everything["items"]) == 5 and (everything["limit"], everything["offset"]) == (5, 0)
    only_2015 = client.get("/catalog/search", params={"q": "people", "year": 2015, "limit": 50}).json()
    assert 0 < only_2015["total"] < everything["total"] and all(i["decision_date"].startswith("2015") for i in only_2015["items"])
    page2 = client.get("/catalog/search", params={"q": "people", "limit": 5, "offset": 5}).json()
    assert {i["source_url"] + "|".join(i["numbers"]) for i in page2["items"]}.isdisjoint(
        {i["source_url"] + "|".join(i["numbers"]) for i in everything["items"]}
    )


def test_nothing_matches_is_an_honest_empty_answer(client, loaded):
    body = client.get("/catalog/search", params={"q": "zzzzqqqq"}).json()
    assert (body["total"], body["items"]) == (0, [])


def test_a_blank_search_is_nothing_not_everything(client, loaded):
    body = client.get("/catalog/search", params={"q": "   "}).json()
    assert body["understood_as"] == "nothing" and body["items"] == []


@pytest.mark.parametrize("params", [{}, {"q": "x" * 201}, {"q": "a", "limit": 0}, {"q": "a", "limit": 51}, {"q": "a", "offset": -1}, {"q": "a", "year": 1500}, {"q": "a", "year": 3000}])
def test_invalid_search_parameters_are_422(client, params):
    assert client.get("/catalog/search", params=params).status_code == 422


def test_the_first_search_on_an_empty_catalog_starts_the_one_time_build(client, jobs):
    body = client.get("/catalog/search", params={"q": "ermita"}).json()

    assert body["total"] == 0 and body["catalog"]["state"] == "empty"
    assert jobs.catalog_builds == [1987] and jobs.catalog_refreshes == 0
    client.get("/catalog/search", params={"q": "ermita again"})
    assert jobs.catalog_builds == [1987, 1987]  # the real queue refuses the second (its lock); the fake just records asks


def test_searching_a_filled_catalog_asks_for_the_daily_refresh_not_a_build(client, loaded, jobs):
    client.get("/catalog/search", params={"q": "ermita"})
    assert jobs.catalog_builds == [] and jobs.catalog_refreshes == 1
    client.get("/catalog/search", params={"q": "people"})
    assert jobs.catalog_refreshes == 1  # once a day


def test_status_reports_progress_against_the_known_total(client, loaded, running):
    status = client.get("/catalog/status").json()
    assert (status["state"], status["months_read"], status["months_known"]) == ("ready", 2, 2)
    assert status["percent"] == 100 and status["entries"] == 157 + 119  # April 2009 + July 2015 G.R. rows, as counted from the raw HTML

    running["build"] = True
    assert client.get("/catalog/status").json()["state"] == "building"


def test_a_build_can_be_started_once(client, jobs):
    first = client.post("/catalog/build").json()
    assert first["started"] is True and jobs.catalog_builds == [1987]
    jobs.catalog_build_running = True
    assert client.post("/catalog/build").json()["started"] is False and jobs.catalog_builds == [1987]


def test_the_search_endpoint_is_fast_and_never_calls_lawphil(client, loaded, services):
    import time

    started = time.perf_counter()
    client.get("/catalog/search", params={"q": "people philippines"})
    assert (time.perf_counter() - started) * 1000 < 250  # a database query plus JSON, no network


def test_search_still_works_when_the_job_queue_is_unreachable(client, loaded, services, monkeypatch):
    def boom():
        raise ConnectionError("the job queue is down (simulated)")

    monkeypatch.setattr(services, "keep_catalog_fresh", boom)
    body = client.get("/catalog/search", params={"q": "180046"})
    assert body.status_code == 200 and body.json()["total"] == 1
