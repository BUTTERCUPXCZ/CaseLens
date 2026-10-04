"""Link formats below were checked against the live site (see Phase 5 probe)."""
from pathlib import Path

import pytest

from caselens.domain.value_objects import GrNumber
from caselens.infrastructure.lawphil.url_scheme import LawphilUrlScheme
from tests.helpers import read_fixture_html

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
BASE = "https://lawphil.net"


@pytest.fixture
def scheme() -> LawphilUrlScheme:
    return LawphilUrlScheme(BASE)


def test_month_index_url(scheme):
    assert scheme.month_index_url(2009, 4) == f"{BASE}/judjuris/juri2009/apr2009/apr2009.html"
    assert scheme.month_index_url(1960, 12) == f"{BASE}/judjuris/juri1960/dec1960/dec1960.html"


@pytest.mark.parametrize(
    "file, token, suffix, year",
    [
        ("gr_180046_2009.html", "180046", None, 2009),
        ("gr_l-10854_1960.html", "l-10854", None, 1960),
        ("gr_l-12091-92_1960.html", "l-12091-92", None, 1960),
        ("gr_207145_so_2015.html", "207145", "so", 2015),
    ],
)
def test_parse_case_link(scheme, file, token, suffix, year):
    link = scheme.parse_case_link(f"{BASE}/judjuris/juri{year}/x/{file}")
    assert (link.number_token, link.suffix, link.year) == (token, suffix, year)


@pytest.mark.parametrize("file", ["am_02-1-1_2009.html", "apr2009.html", "gr_abc_2009.html"])
def test_non_case_files_are_ignored(scheme, file):
    assert scheme.parse_case_link(f"{BASE}/judjuris/juri2009/apr2009/{file}") is None


@pytest.mark.parametrize(
    "gr, file, expected",
    [
        ("180046", "gr_180046_2009.html", True),
        ("180046", "gr_1800460_2009.html", False),  # longer number, not a match
        ("L-12091", "gr_l-12091-92_1960.html", True),  # consolidated case
        ("L-108", "gr_l-10854_1960.html", False),  # prefix of the number, not a match
        ("99289", "gr_99289-90_1993.html", True),
    ],
)
def test_link_matches_gr_number(scheme, gr, file, expected):
    link = scheme.parse_case_link(f"{BASE}/judjuris/juri2000/jan2000/{file}")
    assert link.is_for(GrNumber(gr)) is expected


def test_case_urls_in_real_april_2009_index(scheme):
    html = read_fixture_html("apr2009.html")
    index_url = scheme.month_index_url(2009, 4)
    urls = scheme.case_urls_in_index(index_url, html)
    assert len(urls) == 140  # EXPECTED.md
    assert f"{BASE}/judjuris/juri2009/apr2009/gr_180046_2009.html" in urls


@pytest.mark.parametrize(
    "url, ok",
    [
        (f"{BASE}/judjuris/juri2009/apr2009/gr_180046_2009.html", True),
        ("http://lawphil.net/judjuris/juri2009/apr2009/gr_180046_2009.html", False),
        ("https://lawphil.net.evil.com/judjuris/x.html", False),
        ("https://example.com/judjuris/x.html", False),
        (f"{BASE}/other/page.html", False),
        (f"{BASE}/judjuris/juri2009/apr2009/gr_180046_2009.pdf", False),
        ("file:///etc/passwd", False),
    ],
)
def test_only_official_https_case_urls_are_allowed(scheme, url, ok):
    assert scheme.is_official_case_url(url) is ok
