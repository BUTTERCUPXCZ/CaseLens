"""Separate opinions on an older Lawphil page, read from the REAL page of Marcos v. Manglapus (GR 88211), where the main parser reads none."""
from pathlib import Path

import pytest

from caselens.infrastructure.lawphil.html_decoding import decode_html
from caselens.infrastructure.lawphil.separate_opinions import parse_separate_opinions

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "digest" / "gr_88211_1989.html"


@pytest.fixture(scope="module")
def opinions():
    return parse_separate_opinions(decode_html(FIXTURE.read_bytes(), "text/html"))


def test_every_separate_opinion_on_the_page_is_found_with_its_author_and_side(opinions):
    assert [(o.author, o.kind) for o in opinions] == [
        ("FERNAN, C.J.", "concurring"),
        ("GUTIERREZ, JR., J.", "dissenting"),
        ("CRUZ, J.", "dissenting"),
        ("PARAS, J.", "dissenting"),
        ("PADILLA, J.", "dissenting"),
        ("SARMIENTO, J.", "dissenting"),
    ]


def test_each_opinion_has_its_own_text_and_not_its_footnotes_or_the_next_opinion(opinions):
    by_author = {o.author: o for o in opinions}
    assert by_author["CRUZ, J."].paragraphs[0].startswith("It is my belief that the petitioner")
    assert by_author["PARAS, J."].paragraphs[0].startswith("I dissent. Already, some people refer to us")
    assert all(not text.lower().startswith("footnotes") for o in opinions for text in o.paragraphs)
    assert not any("It is my belief that the petitioner" in text for text in by_author["GUTIERREZ, JR., J."].paragraphs)  # Cruz's text is Cruz's
    assert min(len(o.paragraphs) for o in opinions) >= 7


def test_a_page_with_no_separate_opinion_gives_none():
    assert parse_separate_opinions("<html><body><p>Just a decision.</p></body></html>") == []


def test_the_main_parser_now_reads_them_so_every_page_has_its_opinions():
    from caselens.infrastructure.lawphil.html_parser import LawphilCaseParser

    case = LawphilCaseParser().parse(decode_html(FIXTURE.read_bytes(), "text/html"), "https://lawphil.net/x/gr_88211_1989.html")
    assert [(o.kind, o.author) for o in case.opinions] == [
        ("concurring", "FERNAN"), ("dissenting", "GUTIERREZ, JR."), ("dissenting", "CRUZ"), ("dissenting", "PARAS"), ("dissenting", "PADILLA"), ("dissenting", "SARMIENTO"),
    ]
    assert not any("It is my belief that the petitioner" in line for line in case.full_text.split("\n"))  # the opinions are not part of the decision's own text
