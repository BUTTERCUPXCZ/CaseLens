from datetime import date
from pathlib import Path

import httpx
import pytest

from caselens.domain.errors import CaseNotFoundError, InvalidSourceUrlError
from caselens.domain.value_objects import GrNumber
from caselens.infrastructure.lawphil.case_source import LawphilCaseSource
from caselens.infrastructure.lawphil.http_client import ThrottledPageClient
from caselens.infrastructure.lawphil.url_scheme import LawphilUrlScheme
from tests.fakes import InMemoryMonthIndexRepository
from tests.helpers import read_fixture_html

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
BASE = "https://lawphil.net"
APR_2009 = f"{BASE}/judjuris/juri2009/apr2009/apr2009.html"
TARGET = f"{BASE}/judjuris/juri2009/apr2009/gr_180046_2009.html"


class FakeSite:
    """Serves chosen pages, 404 for everything else, and counts requests."""

    def __init__(self, pages: dict[str, str]) -> None:
        self.pages = pages
        self.requests: list[str] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        self.requests.append(url)
        if url in self.pages:
            return httpx.Response(200, text=self.pages[url])
        return httpx.Response(404)


def build(site: FakeSite, radius=2, today=date(2026, 10, 3)):
    http = httpx.Client(transport=httpx.MockTransport(site.handler))
    pages = ThrottledPageClient(http, 0, 0, sleep=lambda s: None)
    repo = InMemoryMonthIndexRepository()
    source = LawphilCaseSource(
        pages, repo, LawphilUrlScheme(BASE), search_radius=radius, today=lambda: today
    )
    return source, repo


@pytest.fixture
def april_index() -> str:
    return read_fixture_html("apr2009.html")


def test_wrong_claimed_year_is_corrected_by_searching_nearby_years(april_index):
    """The sample reviewer says 2010; the real case is in April 2009."""
    site = FakeSite({APR_2009: april_index})
    source, _ = build(site)

    assert source.locate(GrNumber("180046"), 2010) == [TARGET]
    assert len(site.requests) == 24  # all 12 months of 2010, then all 12 of 2009


def test_second_lookup_makes_no_http_requests(april_index):
    site = FakeSite({APR_2009: april_index})
    source, _ = build(site)
    source.locate(GrNumber("180046"), 2010)
    before = len(site.requests)

    assert source.locate(GrNumber("180046"), 2010) == [TARGET]
    assert len(site.requests) == before


def test_unknown_number_returns_empty_and_never_guesses(april_index):
    site = FakeSite({APR_2009: april_index})
    source, _ = build(site, radius=0)
    assert source.locate(GrNumber("999999"), 2009) == []
    assert len(site.requests) == 12


def test_no_claimed_year_means_no_search():
    site = FakeSite({})
    source, _ = build(site)
    assert source.locate(GrNumber("180046"), None) == []
    assert site.requests == []


def test_primary_decision_is_listed_before_extra_documents():
    index = '<a href="gr_207145_so_2015.html">so</a><a href="gr_207145_2015.html">decision</a>'
    url = f"{BASE}/judjuris/juri2015/jul2015/jul2015.html"
    source, _ = build(FakeSite({url: index}), radius=0)

    assert source.locate(GrNumber("207145"), 2015) == [
        f"{BASE}/judjuris/juri2015/jul2015/gr_207145_2015.html",
        f"{BASE}/judjuris/juri2015/jul2015/gr_207145_so_2015.html",
    ]


def test_missing_page_in_a_past_year_is_cached_but_not_in_the_current_year():
    site = FakeSite({})
    source, repo = build(site, radius=0, today=date(2026, 10, 3))

    source.locate(GrNumber("180046"), 2009)  # past year: 404s are remembered
    source.locate(GrNumber("180046"), 2026)  # current year: a 404 may change later
    assert len(site.requests) == 24

    source.locate(GrNumber("180046"), 2009)
    source.locate(GrNumber("180046"), 2026)
    assert len(site.requests) == 36  # only the current year was requested again
    assert f"{BASE}/judjuris/juri2009/jan2009/jan2009.html" in repo.data
    assert f"{BASE}/judjuris/juri2026/jan2026/jan2026.html" not in repo.data


def test_years_in_the_future_are_never_searched():
    site = FakeSite({})
    source, _ = build(site, radius=2, today=date(2026, 10, 3))
    source.locate(GrNumber("180046"), 2026)
    assert not any("juri2027" in r or "juri2028" in r for r in site.requests)


def test_fetch_returns_the_page():
    site = FakeSite({TARGET: "<html>case</html>"})
    source, _ = build(site)
    assert source.fetch(TARGET) == "<html>case</html>"


def test_fetch_missing_page_raises_not_found():
    source, _ = build(FakeSite({}))
    with pytest.raises(CaseNotFoundError):
        source.fetch(TARGET)


@pytest.mark.parametrize(
    "url", ["http://lawphil.net/judjuris/a.html", "https://evil.example/judjuris/a.html"]
)
def test_fetch_refuses_urls_that_are_not_official(url):
    site = FakeSite({})
    source, _ = build(site)
    with pytest.raises(InvalidSourceUrlError):
        source.fetch(url)
    assert site.requests == []
