"""Regressions found by parsing 25 random real pages from the April 2009 index.
Expected values were read from the raw HTML, not from the parser (see EXPECTED.md)."""
from datetime import date
from pathlib import Path

import pytest

from caselens.domain.value_objects import Disposition
from caselens.infrastructure.lawphil.html_parser import LawphilCaseParser
from tests.helpers import read_fixture_html

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
BASE = "https://lawphil.net/judjuris/juri2009/apr2009/"


def parse(name: str):
    html = read_fixture_html(name)
    return LawphilCaseParser().parse(html, BASE + name)


def test_empty_footnote_on_the_official_page_is_kept_not_dropped():
    """Lawphil's GR 173931 has `<a name="fnt6"></a>` with no text, but the body cites [^6]."""
    case = parse("gr_173931_2009.html")
    assert [f.number for f in case.footnotes] == list(range(1, 61))  # all 60, none missing
    assert case.footnotes[5].number == 6 and case.footnotes[5].text == ""
    assert case.decision_date == date(2009, 4, 2)


def test_ruling_that_spans_several_paragraphs_is_classified_from_all_of_them():
    """GR 183905: 'WHEREFORE, ... G.R. No. 184275 is EXPUNGED ... / ... G.R. No. 183905 is DISMISSED'."""
    case = parse("gr_183905_2009.html")
    assert case.ponente == "TINGA"
    assert case.decision_date == date(2009, 4, 16)
    assert case.disposition is Disposition.DISMISSED
    assert len(case.footnotes) == 72


def test_justices_in_the_signature_table_are_part_of_the_text_in_order():
    """GR 180046 lists its concurring justices in a <table>; they used to be dropped."""
    lines = parse("gr_180046_2009.html").full_text.split("\n")
    start = lines.index("WE CONCUR:")
    block = lines[start : lines.index("C E R T I F I C A T I O N")]

    assert block[1] == "REYNATO S. PUNO Chief Justice"
    assert "LEONARDO A. QUISUMBING Associate Justice" in block
    assert "PRESBITERO J. VELASCO, JR. Associate Justice" in block
    assert block.index("LEONARDO A. QUISUMBING Associate Justice") < block.index(
        "CONSUELO YNARES-SANTIAGO Associate Justice"
    )  # left-to-right, top-to-bottom, as on the page


@pytest.mark.parametrize("name", ["gr_173931_2009.html", "gr_183905_2009.html", "gr_180046_2009.html"])
def test_certification_boilerplate_is_not_counted_as_a_cited_statute(name):
    """Found by real trends: every decision ends 'Pursuant to Section 13, Article VIII of the
    Constitution, I certify ...', which made it the 'most cited' provision (7 of 7 cases).
    Checked on these three pages: it appears only in the certification, nowhere else."""
    case = parse(name)
    assert "C E R T I F I C A T I O N" in case.full_text  # the certification stays in the stored text
    assert all(s.number != "Art. VIII, Sec. 13" for s in case.statutes)


def test_statute_written_with_a_parenthetical_abbreviation_is_found():
    """GR 173931's body says 'Section 11 of Republic Act (R.A.) No. 7722'; it used to yield no statutes."""
    case = parse("gr_173931_2009.html")
    assert ("RA", "7722") in {(s.statute_type.value, s.number) for s in case.statutes}


def test_cited_case_titles_have_no_leading_citing():
    titles = [c.title for c in parse("gr_183905_2009.html").cited_cases]
    assert not any(t.lower().startswith("citing ") for t in titles)
    assert "Turquenza v. Hernando, et al." in titles  # real footnote 34


@pytest.mark.parametrize("name", ["gr_173931_2009.html", "gr_183905_2009.html", "gr_180046_2009.html"])
def test_every_marker_in_the_text_has_a_footnote(name):
    import re

    case = parse(name)
    markers = {int(n) for n in re.findall(r"\[\^(\d+)\]", case.full_text)}
    assert markers <= {f.number for f in case.footnotes}


@pytest.mark.parametrize("name", ["gr_173931_2009.html", "gr_183905_2009.html", "gr_180046_2009.html"])
def test_official_text_has_no_damaged_characters(name):
    """Found through the web app: apostrophes had turned into U+FFFD because the page is
    windows-1252 and was decoded as UTF-8. The stored text is exactly what the Court printed."""
    case = parse(name)
    assert "�" not in case.full_text
    assert not any("�" in f.text for f in case.footnotes)
    assert "�" not in case.raw_html


def test_curly_apostrophes_survive_in_the_stored_text():
    assert "Center’s President" in parse("gr_180046_2009.html").full_text
