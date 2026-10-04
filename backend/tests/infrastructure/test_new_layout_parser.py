"""Decisions from about 2016 on use a second Lawphil layout: `[ G.R. No. 161425. November 23, 2016 ]`, the
party line in capitals (`PETITIONERS, VS. ... RESPONDENTS.`), an unspaced `DECISION`, and footnote markers
`<a class="nt">1</a>` with no anchor name. Expected values were read from the saved pages
(tests/fixtures/digest/, downloaded from lawphil.net)."""
from datetime import date
from pathlib import Path

import pytest

from caselens.domain.value_objects import DocType
from caselens.infrastructure.lawphil.html_decoding import decode_html
from caselens.infrastructure.lawphil.html_parser import LawphilCaseParser

DIGEST_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "digest"

# file, G.R. no., date, division, ponente, doc type
PAGES = [
    ("gr_161425_2016.html", "161425", date(2016, 11, 23), "THIRD DIVISION", "PEREZ", DocType.RESOLUTION),
    ("gr_196510_2018.html", "196510", date(2018, 9, 12), "FIRST DIVISION", "BERSAMIN", DocType.DECISION),
    ("gr_240774_2021.html", "240774", date(2021, 3, 3), "FIRST DIVISION", "GAERLAN", DocType.DECISION),
    ("gr_221664_2022.html", "221664", date(2022, 6, 27), "SECOND DIVISION", "KHO, JR.", DocType.DECISION),
    ("gr_272689_2024.html", "272689", date(2024, 10, 16), "FIRST DIVISION", "HERNANDO", DocType.DECISION),
]


def parse(name: str):
    html = decode_html((DIGEST_FIXTURES / name).read_bytes(), "text/html")
    return LawphilCaseParser().parse(html, f"https://lawphil.net/x/{name}")


@pytest.mark.parametrize(("name", "gr_no", "decided", "division", "ponente", "doc_type"), PAGES)
def test_reads_the_header_of_the_new_layout(name, gr_no, decided, division, ponente, doc_type):
    case = parse(name)
    assert case.gr_no.value == gr_no
    assert case.decision_date == decided
    assert case.division == division
    assert case.ponente == ponente
    assert case.doc_type is doc_type
    assert case.title and "PETITIONER" in case.title.upper()


def test_footnotes_of_the_new_layout_are_read_and_markers_stay_in_the_text():
    case = parse("gr_196510_2018.html")
    first = case.footnotes[0]
    assert first.number == 1
    assert first.text.startswith("Rollo, pp. 47-58; penned by Associate Justice Samuel H. Gaerlan")
    assert len(case.footnotes) >= 14
    assert "September 30, 2009,[^1]" in case.full_text


@pytest.mark.parametrize("name", [page[0] for page in PAGES])
def test_the_ruling_is_found_in_the_new_layout(name):
    assert parse(name).disposition.value != "unknown"
