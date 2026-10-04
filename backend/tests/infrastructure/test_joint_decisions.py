"""Joint decisions on REAL pages (gr_211972_2015.html and gr_148263_2009.html): one page, several G.R. numbers.
Read from the pages: 211972 prints 'G.R. No. 211972 July 22, 2015' then, after the first party block, a separate
'G.R. No. 212045' line; 148263 prints 'G.R. Nos. 148263 and 148271-72 April 21, 2009' on one line."""
from datetime import date

import pytest

from caselens.domain.services.citation_matcher import CitationMatcher
from caselens.domain.value_objects import ClaimedCitation, GrNumber, MatchStatus
from caselens.infrastructure.db.repositories import SqlCaseRepository
from caselens.infrastructure.lawphil.html_parser import LawphilCaseParser
from tests.helpers import parse_official_case, read_fixture_html

BASE = "https://lawphil.net/judjuris"


def parse(name: str, year: int, month: str):
    return LawphilCaseParser().parse(read_fixture_html(name), f"{BASE}/juri{year}/{month}{year}/{name}")


@pytest.fixture(scope="module")
def go_v_estate():
    return parse("gr_211972_2015.html", 2015, "jul")


@pytest.fixture(scope="module")
def david():
    return parse("gr_148263_2009.html", 2009, "apr")


def test_numbers_on_their_own_caption_lines_are_all_read(go_v_estate):
    assert go_v_estate.gr_no == GrNumber("211972")  # the first number stays the page's own
    assert go_v_estate.numbers == ("211972", "212045")
    assert go_v_estate.decision_date == date(2015, 7, 22)


def test_a_one_line_label_with_a_range_is_expanded(david):
    assert david.gr_no == GrNumber("148263")
    assert david.numbers == ("148263", "148271", "148272")


def test_an_ordinary_decision_has_just_its_one_number():
    assert parse_official_case().numbers == ("180046",)


@pytest.mark.parametrize("cited", ["211972", "212045"])
def test_citing_either_number_of_a_joint_decision_is_correct(go_v_estate, cited):
    claimed = ClaimedCitation(GrNumber(cited), f"GR no {cited}", claimed_year=2015)
    result = CitationMatcher().match(claimed, go_v_estate)
    assert "gr_no" not in result.mismatches and result.status is MatchStatus.MATCH


def test_a_number_that_is_not_part_of_the_decision_is_still_a_mismatch(go_v_estate):
    claimed = ClaimedCitation(GrNumber("212046"), "GR no 212046", claimed_year=2015)
    result = CitationMatcher().match(claimed, go_v_estate)
    assert result.mismatches["gr_no"] == {"claimed": "212046", "official": "211972"}


@pytest.mark.db
def test_a_stored_joint_decision_is_found_by_its_second_number_and_survives_a_round_trip(db_session, go_v_estate):
    repo = SqlCaseRepository(db_session)
    stored = repo.add(go_v_estate)
    db_session.expire_all()

    assert repo.get(stored.id).numbers == ("211972", "212045")
    assert [c.id for c in repo.find_by_gr_no(GrNumber("212045"))] == [stored.id]
    assert [c.id for c in repo.find_by_gr_no(GrNumber("211972"))] == [stored.id]
    assert repo.find_by_gr_no(GrNumber("212046")) == []


@pytest.mark.db
def test_rows_stored_before_this_existed_fall_back_to_their_one_number(db_session):
    from dataclasses import replace

    repo = SqlCaseRepository(db_session)
    legacy = repo.add(replace(parse_official_case(), numbers=()))  # an old row has no numbers array
    assert repo.get(legacy.id).all_numbers == ("180046",)
