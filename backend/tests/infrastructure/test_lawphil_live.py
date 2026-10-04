"""Hits the real lawphil.net (throttled to 1 request/second). Run with: pytest -m live"""
import httpx
import pytest

from caselens.domain.value_objects import GrNumber
from caselens.infrastructure.config import get_settings
from caselens.infrastructure.lawphil.case_source import LawphilCaseSource
from caselens.infrastructure.lawphil.http_client import ThrottledPageClient
from caselens.infrastructure.lawphil.url_scheme import LawphilUrlScheme
from tests.fakes import InMemoryMonthIndexRepository

pytestmark = pytest.mark.live

TARGET = "https://lawphil.net/judjuris/juri2009/apr2009/gr_180046_2009.html"


class CountingHttp(httpx.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.count = 0

    def get(self, *args, **kwargs):
        self.count += 1
        return super().get(*args, **kwargs)


def make_source(radius: int):
    settings = get_settings()
    http = CountingHttp(
        headers={"User-Agent": settings.lawphil_user_agent},
        timeout=settings.lawphil_timeout_seconds,
        follow_redirects=True,
    )
    pages = ThrottledPageClient(http, settings.lawphil_min_interval_seconds, settings.lawphil_max_retries)
    source = LawphilCaseSource(
        pages, InMemoryMonthIndexRepository(), LawphilUrlScheme(settings.lawphil_base_url), search_radius=radius
    )
    return source, http


def test_wrong_year_2010_resolves_to_the_real_2009_case_and_second_call_is_free():
    source, http = make_source(radius=1)

    assert source.locate(GrNumber("180046"), 2010) == [TARGET]
    first_cost = http.count
    assert first_cost > 0

    assert source.locate(GrNumber("180046"), 2010) == [TARGET]
    assert http.count == first_cost  # cache hit: zero HTTP requests


def test_old_style_l_number_resolves():
    """Index for Jan 1960 listed gr_l-10854_1960.html during the Phase 5 probe."""
    source, _ = make_source(radius=0)
    urls = source.locate(GrNumber("L-10854"), 1960)
    assert urls == ["https://lawphil.net/judjuris/juri1960/jan1960/gr_l-10854_1960.html"]


def test_consolidated_old_style_number_resolves():
    """Probe listed gr_l-12091-92_1960.html: searching the first number must find it."""
    source, _ = make_source(radius=0)
    urls = source.locate(GrNumber("L-12091"), 1960)
    assert urls == ["https://lawphil.net/judjuris/juri1960/jan1960/gr_l-12091-92_1960.html"]


def test_number_that_does_not_exist_returns_nothing():
    source, _ = make_source(radius=0)
    assert source.locate(GrNumber("999999"), 2009) == []


def test_fetch_and_parse_the_real_page():
    from caselens.infrastructure.lawphil.html_parser import LawphilCaseParser

    source, _ = make_source(radius=0)
    case = LawphilCaseParser().parse(source.fetch(TARGET), TARGET)
    assert str(case.gr_no) == "180046" and len(case.footnotes) == 42
