"""The monthly-list parser on four real pages. Expected counts and rows are in
tests/fixtures/catalog/EXPECTED.md, read from the raw HTML before the parser was written."""
from datetime import date
from pathlib import Path

import pytest

from caselens.application.ports.catalog import ParsedIndex
from caselens.infrastructure.lawphil.catalog_parser import LawphilCatalogParser
from caselens.infrastructure.lawphil.html_decoding import decode_html

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "catalog"
BASE = "https://lawphil.net/judjuris"


def parse(name: str, year: int, month: str) -> ParsedIndex:
    html = decode_html((FIXTURES / name).read_bytes(), "text/html")
    return LawphilCatalogParser().parse(html, f"{BASE}/juri{year}/{month}{year}/{month}{year}.html")


@pytest.fixture(scope="module")
def apr2009() -> ParsedIndex:
    return parse("apr2009.html", 2009, "apr")


@pytest.mark.parametrize(
    "name, year, month, gr_rows, other",
    [
        ("mar1987.html", 1987, "mar", 52, {}),
        ("jun1995.html", 1995, "jun", 52, {"am": 11, "ac": 1}),
        ("apr2009.html", 2009, "apr", 157, {"am": 20, "bm": 1, "ac": 2}),
        ("jul2015.html", 2015, "jul", 119, {"am": 13, "ac": 6}),
    ],
)
def test_row_counts_match_the_raw_html(name, year, month, gr_rows, other):
    parsed = parse(name, year, month)
    assert len(parsed.entries) == gr_rows
    assert parsed.other_kinds == other  # administrative matters are counted, not returned
    assert parsed.link_rows == gr_rows + sum(other.values())
    assert parsed.unreadable == 0 and not parsed.looks_broken


def test_the_wrapper_row_is_not_a_case(apr2009):
    # the wrapper row contains the whole page; counting it would add a 158th "case"
    assert len(apr2009.entries) == 157
    assert all(len(entry.title) < 300 for entry in apr2009.entries)


def test_first_and_last_rows_of_april_2009(apr2009):
    first, last = apr2009.entries[0], apr2009.entries[-1]
    assert (first.numbers, first.decision_date, first.title) == (
        ("146408",), date(2009, 4, 30), "Philippine Airlines, Inc. vs. Enrique Ligan, et al.",
    )
    assert first.source_url == f"{BASE}/juri2009/apr2009/gr_146408_2009.html"
    assert (last.numbers, last.decision_date) == (("179240", "179241"), date(2009, 4, 1))


def test_april_2009_has_157_rows_but_140_pages(apr2009):
    assert len({entry.source_url for entry in apr2009.entries}) == 140


def test_a_row_whose_label_and_link_disagree_keeps_both(apr2009):
    """Lawphil's own list: label 155573 links to gr_154473; label 181726 links to a sibling's page."""
    by_label = {entry.numbers[0]: entry for entry in apr2009.entries}
    typo = by_label["155573"]
    assert typo.source_url.endswith("gr_154473_2009.html") and typo.gr_no.value == "154473"
    assert typo.also_decided_with == ("155573",)  # not decided "with" anything; the label differs from the link
    sibling = by_label["181726"]
    assert sibling.source_url.endswith("gr_181377_2009.html")


def test_joint_decisions_are_searchable_by_every_number(apr2009):
    joint = {entry.numbers: entry for entry in apr2009.entries}
    assert ("164785", "165636") in joint and ("148263", "148271", "148272") in joint
    assert joint[("170270", "179411")].also_decided_with == ("179411",)


def test_1987_old_style_numbers_and_the_two_rows_without_a_space_in_the_date():
    parsed = parse("mar1987.html", 1987, "mar")
    first = parsed.entries[0]
    assert (first.numbers, first.gr_no.value, first.decision_date) == (("L-28156",), "L-28156", date(1987, 3, 31))
    assert first.source_url.endswith("gr_l-28156_1987.html")
    odd = {e.numbers[0]: e.decision_date for e in parsed.entries}
    assert odd["L-38513"] == date(1987, 3, 31) and odd["L-70360"] == date(1987, 3, 11)


def test_2015_joint_rows():
    parsed = parse("jul2015.html", 2015, "jul")
    joint = {e.numbers: e for e in parsed.entries}
    assert joint[("211972", "212045")].decision_date == date(2015, 7, 22)
    assert joint[("209353", "209354", "211733", "211734")].source_url.endswith("gr_209353_2015.html")


def test_a_page_with_case_links_but_nothing_readable_is_reported_as_broken():
    html = '<table><tr><td><a href="gr_oops_2009.html">?</a></td><td>x</td></tr></table>'
    parsed = LawphilCatalogParser().parse(html, f"{BASE}/juri2009/apr2009/apr2009.html")
    assert (parsed.entries, parsed.link_rows, parsed.unreadable) == ([], 1, 1)
    assert parsed.looks_broken


def test_an_empty_page_is_not_broken_just_empty():
    parsed = LawphilCatalogParser().parse("<html><body>nothing</body></html>", f"{BASE}/x.html")
    assert (parsed.entries, parsed.link_rows) == ([], 0) and not parsed.looks_broken
