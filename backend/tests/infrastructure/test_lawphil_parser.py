"""Parser tests run on the saved real page. Expected values come from
tests/fixtures/EXPECTED.md, which was written by reading the actual HTML."""
import re
from datetime import date
from pathlib import Path

import pytest

from caselens.domain.errors import CaseParseError
from caselens.domain.value_objects import Disposition, DocType, StatuteType
from caselens.infrastructure.lawphil.html_parser import LawphilCaseParser
from tests.helpers import read_fixture_html

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
URL = "https://lawphil.net/judjuris/juri2009/apr2009/gr_180046_2009.html"


@pytest.fixture(scope="module")
def html() -> str:
    return read_fixture_html("gr_180046_2009.html")


@pytest.fixture(scope="module")
def case(html):
    return LawphilCaseParser().parse(html, URL)


def test_header_fields(case):
    assert str(case.gr_no) == "180046"
    assert case.decision_date == date(2009, 4, 2)
    assert case.division == "EN BANC"
    assert case.doc_type is DocType.DECISION
    assert case.ponente == "CARPIO"
    assert case.source_url == URL


def test_title_is_party_block_up_to_respondents(case):
    assert case.title == (
        "REVIEW CENTER ASSOCIATION OF THE PHILIPPINES, Petitioner, vs. EXECUTIVE SECRETARY "
        "EDUARDO ERMITA and COMMISSION ON HIGHER EDUCATION represented by its Chairman "
        "ROMULO L. NERI, Respondents."
    )


def test_disposition_is_granted(case):
    assert case.disposition is Disposition.GRANTED


def test_decision_has_42_footnotes_numbered_1_to_42(case):
    assert [f.number for f in case.footnotes] == list(range(1, 43))
    assert case.footnotes[0].anchor == "fnt1"
    assert case.footnotes[0].text.startswith("Rollo, pp. 35-37.")


def test_every_marker_in_text_has_a_footnote(case):
    markers = {int(n) for n in re.findall(r"\[\^(\d+)\]", case.full_text)}
    assert markers == {f.number for f in case.footnotes}


def test_footnote_deep_link(case):
    assert case.footnote_url(19) == URL + "#fnt19"


def test_separate_opinion_is_split_out_with_its_own_13_footnotes(case):
    assert len(case.opinions) == 1
    opinion = case.opinions[0]
    assert opinion.kind == "concurring"
    assert opinion.author == "BRION"
    assert opinion.text.startswith("I concur with the ponencia")
    assert [f.number for f in opinion.footnotes] == list(range(1, 14))
    assert opinion.footnotes[0].anchor == "fnt1b"


def test_opinion_text_is_not_mixed_into_the_decision(case):
    assert "I concur with the ponencia" not in case.full_text
    assert "SEPARATE CONCURRING OPINION" not in case.full_text


def test_full_text_has_no_watermark_or_navigation_junk(case):
    assert not re.search(r"1a(?:w|vv)p", case.full_text)
    assert "The Lawphil Project" not in case.full_text
    assert "WHEREFORE, we GRANT" in case.full_text.replace("WHEREFORE ,", "WHEREFORE,")


def test_raw_html_is_kept_verbatim(case, html):
    assert case.raw_html == html


def test_statutes_found_in_the_decision(case):
    found = {(s.statute_type, s.number) for s in case.statutes}
    for expected in [
        (StatuteType.REPUBLIC_ACT, "7722"),
        (StatuteType.REPUBLIC_ACT, "8981"),
        (StatuteType.REPUBLIC_ACT, "3019"),
        (StatuteType.EXECUTIVE_ORDER, "292"),
        (StatuteType.EXECUTIVE_ORDER, "566"),
        (StatuteType.CONSTITUTION, "Art. VI, Sec. 1"),
    ]:
        assert expected in found


def test_cited_cases_found_in_body_and_footnotes(case):
    by_title = {c.title: c for c in case.cited_cases}
    assert by_title["Ople v. Torres"].source == "body"
    assert by_title["LPBS Commercial, Inc. v. Amila"].gr_no == "147443"
    assert by_title["People v. Cuaresma"].gr_no == "67787"
    assert by_title["Santiago v. Vasquez"].gr_no == "99289"
    assert by_title["Republic v. Lacap"].gr_no == "158253"
    assert by_title["Executive Secretary v. Southwing Heavy Industries, Inc."].gr_no == "164171"
    assert by_title["Metropolitan Manila Development Authority v. Viron Transportation Co., Inc."].gr_no == "170656"
    assert "Kilusang Mayo Uno v. Director-General, National Economic Development Authority" in by_title


def test_page_without_gr_line_is_rejected():
    with pytest.raises(CaseParseError):
        LawphilCaseParser().parse("<html><body><p>Nothing here</p></body></html>", URL)
