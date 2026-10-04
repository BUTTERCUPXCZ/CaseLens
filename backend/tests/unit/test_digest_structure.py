"""Where the Court's own Facts, Issues and final ruling are, on 31 real decisions (1988-2025).

Every number below was read by hand from the saved pages (see tests/fixtures/digest/EXPECTED.md). Paragraph
numbers are positions in `Case.full_text.split("\\n")`; ranges include both ends. `None` = the Court wrote no
such heading, so nothing may be returned (an AI picks it later, and it is shown as a suggestion).
"""
import pytest

from caselens.domain.digest import ParagraphRange, SectionKind
from caselens.domain.services.dispositive_extractor import DispositiveExtractor
from caselens.domain.services.heading_sections import HeadingSections
from caselens.domain.services.ruling_locator import RulingLocator

from ..helpers import digest_paragraphs

# file: (facts, issues, final ruling)
EXPECTED = {
    "gr_71464_1988.html": (None, None, (38, 38)),
    "gr_71681_1989.html": (None, None, (35, 35)),
    "gr_84272_1991.html": (None, None, (59, 59)),
    "gr_37012_1992.html": (None, None, (56, 56)),
    "gr_89967_1994.html": (None, None, (36, 36)),
    "gr_117246_1995.html": (None, None, (62, 62)),
    "gr_119935_1997.html": (None, None, (35, 35)),
    "gr_125548_1998.html": ((17, 25), None, (47, 47)),
    "gr_130969_2000.html": (None, None, (81, 82)),
    "gr_133922_2001.html": (None, None, (442, 442)),
    "gr_127152_2003.html": (None, None, (36, 36)),
    "gr_160890_2004.html": (None, None, (33, 33)),
    "gr_161811_2006.html": (None, None, (54, 55)),
    "gr_173256_2007.html": (None, None, (33, 33)),
    "gr_148263_2009.html": ((9, 14), (34, 37), (52, 52)),
    "gr_165678_2009.html": ((9, 49), (63, 67), (92, 93)),
    "gr_173931_2009.html": (None, None, (53, 53)),
    "gr_180046_2009.html": ((9, 62), (64, 66), (132, 132)),
    "gr_183905_2009.html": (None, None, (144, 146)),
    "gr_173081_2010.html": ((9, 20), (22, 22), (43, 43)),
    "gr_174941_2012.html": (None, None, (171, 172)),
    "gr_172846_2013.html": (None, None, (66, 67)),
    "gr_175483_2015.html": ((9, 28), None, (80, 80)),
    "gr_211972_2015.html": ((11, 21), (35, 35), (66, 66)),
    "gr_161425_2016.html": (None, None, (67, 67)),
    "gr_196510_2018.html": ((11, 21), (37, 38), (58, 58)),
    "gr_233850_2019.html": ((8, 17), (26, 26), (84, 84)),
    "gr_240774_2021.html": ((8, 41), None, (150, 150)),
    "gr_221664_2022.html": ((8, 18), (37, 37), (79, 80)),
    "gr_272689_2024.html": ((8, 16), (34, 34), (79, 79)),
    "gr_260071_2025.html": ((8, 13), (37, 37), (69, 71)),
}


def as_range(pair: tuple[int, int] | None) -> ParagraphRange | None:
    return None if pair is None else ParagraphRange(*pair)


@pytest.mark.parametrize("name", EXPECTED)
def test_the_final_ruling_is_the_paragraphs_before_the_last_so_ordered(name):
    paragraphs = digest_paragraphs(name)
    assert RulingLocator().locate(paragraphs) == as_range(EXPECTED[name][2])


@pytest.mark.parametrize("name", EXPECTED)
def test_facts_are_returned_only_under_the_courts_own_heading(name):
    found = HeadingSections().find(digest_paragraphs(name))
    assert found.get(SectionKind.FACTS) == as_range(EXPECTED[name][0])


@pytest.mark.parametrize("name", EXPECTED)
def test_issues_are_returned_only_under_the_courts_own_heading(name):
    found = HeadingSections().find(digest_paragraphs(name))
    assert found.get(SectionKind.ISSUES) == as_range(EXPECTED[name][1])


def test_a_quoted_lower_court_ruling_is_not_mistaken_for_the_final_one():
    # GR 260071 quotes the RTC's and the CA's WHEREFORE earlier on (paragraphs 16 and 27).
    paragraphs = digest_paragraphs("gr_260071_2025.html")
    ruling = DispositiveExtractor().extract(paragraphs)
    assert ruling is not None
    assert ruling.startswith("ACCORDINGLY, the Petition for Review is PARTLY GRANTED")


def test_a_ruling_that_opens_with_accordingly_is_found():
    ruling = DispositiveExtractor().extract(digest_paragraphs("gr_221664_2022.html"))
    assert ruling is not None and ruling.startswith("ACCORDINGLY, the foregoing considered")


def test_the_ruling_of_a_decision_with_several_paragraphs_keeps_all_of_them():
    ruling = DispositiveExtractor().extract(digest_paragraphs("gr_183905_2009.html"))
    assert ruling is not None
    assert "EXPUNGED" in ruling and "DISMISSED" in ruling and "DELETED" in ruling


def test_nothing_is_invented_when_there_is_no_ruling():
    assert RulingLocator().locate(["Some text.", "More text."]) is None
    assert HeadingSections().find(["Some text.", "More text."]) == {}
