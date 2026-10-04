"""Year discovery on the real saved master page and year pages, and the one-request-per-second rule."""
from datetime import date
from pathlib import Path

import httpx

from caselens.infrastructure.lawphil.catalog_source import LawphilIndexFetcher, LawphilYearDiscovery
from caselens.infrastructure.lawphil.http_client import ThrottledPageClient
from caselens.infrastructure.lawphil.url_scheme import LawphilUrlScheme
from tests.infrastructure.test_http_client import FakeTime

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "catalog"
BASE = "https://lawphil.net"
TODAY = date(2026, 10, 3)


def serve(routes: dict[str, bytes], clock: FakeTime | None = None) -> tuple[ThrottledPageClient, list[str]]:
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        body = routes.get(str(request.url))
        return httpx.Response(200, content=body, headers={"content-type": "text/html"}) if body is not None else httpx.Response(404)

    clock = clock or FakeTime()
    pages = ThrottledPageClient(httpx.Client(transport=httpx.MockTransport(handler)), 1.0, 0, sleep=clock.sleep, clock=clock.clock)
    return pages, requested


def discovery(routes, clock=None) -> tuple[LawphilYearDiscovery, list[str]]:
    pages, requested = serve(routes, clock)
    return LawphilYearDiscovery(pages, LawphilUrlScheme(BASE), BASE, today=lambda: TODAY), requested


def read(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def test_years_come_from_the_real_master_page_and_future_years_are_ignored():
    found, _ = discovery({f"{BASE}/judjuris/judjuris.html": read("judjuris.html")})
    years = found.years()
    assert years[0] == 1901 and years[-1] == 2026  # the page also links 2027-2040: not yet happened
    assert len([y for y in years if y >= 1987]) == 40  # 1987 .. 2026
    assert years == sorted(years)


def test_months_come_from_the_year_page_so_missing_months_are_never_requested():
    found, requested = discovery({f"{BASE}/judjuris/juri2023/juri2023.html": read("year2023.html")})
    months = found.months(2023)
    assert [m.month for m in months] == [1, 2, 3, 4, 6, 7, 8, 10, 11, 12]  # no May (5) and no September (9)
    assert months[0].url == f"{BASE}/judjuris/juri2023/jan2023/jan2023.html"
    assert requested == [f"{BASE}/judjuris/juri2023/juri2023.html"]  # one request, no guessing


def test_a_year_in_progress_lists_only_the_months_that_exist_so_far():
    found, _ = discovery({f"{BASE}/judjuris/juri2026/juri2026.html": read("year2026.html")})
    assert [m.month for m in found.months(2026)] == [1, 2, 4, 8]


def test_a_year_page_that_does_not_exist_has_no_months_and_is_not_an_error():
    found, _ = discovery({})
    assert found.months(1950) == [] and found.years() == []


def test_list_pages_are_requested_at_most_once_per_second():
    clock = FakeTime()
    pages, requested = serve({f"{BASE}/a": b"x", f"{BASE}/b": b"y", f"{BASE}/c": b"z"}, clock)
    fetcher = LawphilIndexFetcher(pages)

    assert [fetcher.fetch(f"{BASE}/{n}") for n in "abc"] == ["x", "y", "z"]
    assert clock.sleeps == [1.0, 1.0]  # never faster than the rule, however fast the crawl loop runs


def test_a_missing_list_page_is_none():
    pages, _ = serve({})
    assert LawphilIndexFetcher(pages).fetch(f"{BASE}/nope.html") is None
