"""Insight rules on the real saved pages. Expected values were read from the pages
(see the signature-block listings in EXPECTED.md), not produced by the code under test."""
from pathlib import Path

import pytest

from caselens.domain.services.dispositive_extractor import DispositiveExtractor
from caselens.domain.services.insight_builder import CaseInsightBuilder
from caselens.domain.services.signature_reader import SignatureReader
from caselens.domain.value_objects import Disposition, StatuteType
from caselens.infrastructure.lawphil.html_parser import LawphilCaseParser
from tests.helpers import OFFICIAL_URL, parse_official_case, read_fixture_html

BASE = "https://lawphil.net/judjuris/juri2009/apr2009/"

GR_180046_CONCURRING = [
    "REYNATO S. PUNO", "LEONARDO A. QUISUMBING", "CONSUELO YNARES-SANTIAGO",
    "MA. ALICIA AUSTRIA-MARTINEZ", "RENATO C. CORONA", "CONCHITA CARPIO MORALES",
    "DANTE O. TINGA", "MINITA V. CHICO-NAZARIO", "PRESBITERO J. VELASCO, JR.",
    "ANTONIO EDUARDO B. NACHURA", "ARTURO D. BRION", "TERESITA J. LEONARDO-DE CASTRO",
    "DIOSDADO M. PERALTA",
]


def parse(name: str):
    html = read_fixture_html(name)
    return LawphilCaseParser().parse(html, BASE + name)


def lines(case) -> list[str]:
    return case.full_text.split("\n")


def test_concurring_justices_of_gr_180046_in_page_order():
    assert SignatureReader().concurring_justices(lines(parse_official_case())) == GR_180046_CONCURRING


def test_division_chairman_suffix_is_not_part_of_the_name():
    names = SignatureReader().concurring_justices(lines(parse("gr_183905_2009.html")))
    assert names == ["LEONARDO A. QUISUMBING", "CONCHITA CARPIO MORALES", "PRESBITERO J. VELASCO, JR.", "ARTURO D. BRION"]


def test_no_concur_block_means_no_justices():
    assert SignatureReader().concurring_justices(["Just text", "More text"]) == []


def test_ruling_is_the_verbatim_dispositive_paragraphs():
    ruling = DispositiveExtractor().extract(lines(parse_official_case()))
    assert ruling.startswith("WHEREFORE")
    assert "we GRANT the petition and the petition-in-intervention" in ruling
    assert "SO ORDERED" not in ruling


def test_multi_paragraph_ruling_keeps_every_paragraph_up_to_so_ordered():
    ruling = DispositiveExtractor().extract(lines(parse("gr_183905_2009.html")))
    assert "G.R. No. 184275 is EXPUNGED" in ruling and "G.R. No. 183905 is DISMISSED" in ruling
    assert "SO ORDERED" not in ruling


def test_no_wherefore_means_no_ruling():
    assert DispositiveExtractor().extract(["Facts.", "Discussion."]) is None


def test_case_insights_for_gr_180046():
    case = parse_official_case()
    case.id = 7
    insights = CaseInsightBuilder().build(case)

    assert (insights.case_id, insights.gr_no, insights.source_url) == (7, "180046", OFFICIAL_URL)
    assert (insights.ponente, insights.division, insights.disposition) == ("CARPIO", "EN BANC", Disposition.GRANTED)
    assert insights.concurring_justices == GR_180046_CONCURRING
    assert [(o.kind, o.author) for o in insights.opinions] == [("concurring", "BRION")]
    assert insights.footnote_count == 42
    assert insights.word_count == len(case.full_text.split())
    assert (StatuteType.EXECUTIVE_ORDER, "566") in {(s.statute_type, s.number) for s in insights.statutes}


def test_cited_cases_link_to_the_footnote_that_cites_them():
    """Footnote numbers were read from the page: 18 = LPBS v. Amila, 19 = People v. Cuaresma,
    20 = Santiago v. Vasquez (cited again 'citing'), body mention of Ople has no footnote."""
    by_title = {c.title: c for c in parse_official_case().cited_cases}
    assert by_title["LPBS Commercial, Inc. v. Amila"].footnote_number == 18
    assert by_title["People v. Cuaresma"].footnote_number == 19
    assert by_title["Santiago v. Vasquez"].footnote_number == 20
    assert by_title["Ople v. Torres"].footnote_number is None
