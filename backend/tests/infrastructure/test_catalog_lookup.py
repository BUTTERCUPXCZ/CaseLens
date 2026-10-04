"""G.R. lookups through the catalog (C4): no year needed, no index pages requested."""
import httpx

from caselens.application.use_cases.search_case import SearchCaseByGrNumber, SearchStatus
from caselens.domain.entities import CatalogEntry, IndexPage
from caselens.domain.value_objects import GrNumber
from caselens.infrastructure.lawphil.case_source import LawphilCaseSource
from caselens.infrastructure.lawphil.http_client import ThrottledPageClient
from caselens.infrastructure.lawphil.url_scheme import LawphilUrlScheme
from tests.fakes import FakeJobQueue, InMemoryCaseRepository, InMemoryCatalogRepository, InMemoryMonthIndexRepository

BASE = "https://lawphil.net"
TARGET = f"{BASE}/judjuris/juri2009/apr2009/gr_180046_2009.html"
APR = IndexPage(2009, 4, f"{BASE}/judjuris/juri2009/apr2009/apr2009.html")


def catalog_with_real_row() -> InMemoryCatalogRepository:
    catalog = InMemoryCatalogRepository()
    catalog.replace_month(
        APR,
        [
            CatalogEntry(GrNumber("180046"), ("180046",), "Review Center Association of the Philippines vs. Executive Secretary Eduardo Ermita", None, TARGET, APR.url),
            CatalogEntry(GrNumber("211972"), ("211972", "212045"), "Joint vs. Joint", None, f"{BASE}/judjuris/juri2015/jul2015/gr_211972_2015.html", APR.url),
        ],
    )
    return catalog


def source(catalog, requested):
    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        return httpx.Response(404)

    pages = ThrottledPageClient(httpx.Client(transport=httpx.MockTransport(handler)), 0, 0, sleep=lambda s: None)
    return LawphilCaseSource(pages, InMemoryMonthIndexRepository(), LawphilUrlScheme(BASE), catalog=catalog)


def test_a_number_the_catalog_knows_is_located_with_no_year_and_no_request():
    requested: list[str] = []
    assert source(catalog_with_real_row(), requested).locate(GrNumber("180046"), None) == [TARGET]
    assert requested == []


def test_the_wrong_year_does_not_matter_when_the_catalog_knows_the_number():
    requested: list[str] = []
    assert source(catalog_with_real_row(), requested).locate(GrNumber("180046"), 1998) == [TARGET]  # the case is from 2009
    assert requested == []


def test_the_second_number_of_a_joint_decision_opens_the_decisions_page():
    requested: list[str] = []
    urls = source(catalog_with_real_row(), requested).locate(GrNumber("212045"), None)
    assert urls == [f"{BASE}/judjuris/juri2015/jul2015/gr_211972_2015.html"]


def test_a_number_the_catalog_does_not_know_falls_back_to_the_month_scan():
    requested: list[str] = []
    assert source(catalog_with_real_row(), requested).locate(GrNumber("999999"), 2009) == []
    assert len(requested) == 60  # the old scan: the claimed year +/- 2 = 5 years x 12 months


def test_no_catalog_entry_and_no_year_still_never_guesses():
    requested: list[str] = []
    assert source(InMemoryCatalogRepository(), requested).locate(GrNumber("180046"), None) == []
    assert requested == []


def test_search_by_number_without_a_year_is_pending_when_lawphil_lists_it():
    jobs = FakeJobQueue()
    search = SearchCaseByGrNumber(InMemoryCaseRepository(), jobs, catalog_with_real_row())

    result = search.execute(GrNumber("180046"), None)

    assert result.status is SearchStatus.PENDING and jobs.fetch_calls == [("180046", None)]


def test_search_by_number_without_a_year_still_asks_for_one_when_nothing_knows_it():
    jobs = FakeJobQueue()
    search = SearchCaseByGrNumber(InMemoryCaseRepository(), jobs, catalog_with_real_row())

    assert search.execute(GrNumber("999999"), None).status is SearchStatus.NEEDS_YEAR
    assert jobs.fetch_calls == []
