from datetime import date

import pytest

from caselens.domain.services.citation_matcher import CitationMatcher
from caselens.domain.value_objects import ClaimedCitation, GrNumber, MatchStatus
from tests.helpers import parse_official_case


@pytest.fixture(scope="module")
def official():
    return parse_official_case()


def claim(**overrides) -> ClaimedCitation:
    fields = dict(gr_number=GrNumber("180046"), raw="GR no 180046")
    fields.update(overrides)
    return ClaimedCitation(**fields)


def test_the_sample_reviewers_citation_is_a_year_mismatch(official):
    """Real case: reviewer says April 2, 2010; the official decision is April 2, 2009."""
    result = CitationMatcher().match(
        claim(
            title="Review Center v Ermita",
            claimed_date=date(2010, 4, 2),
            claimed_year=2010,
            reporter="538 SCRA 428",
        ),
        official,
    )
    assert result.status is MatchStatus.MISMATCH
    assert result.mismatches == {"year": {"claimed": 2010, "official": 2009}}
    assert result.unverified == ["reporter"]  # Lawphil's text cannot confirm it either way


def test_correct_citation_matches(official):
    result = CitationMatcher().match(
        claim(title="Review Center v. Ermita", claimed_date=date(2009, 4, 2), claimed_year=2009),
        official,
    )
    assert result.status is MatchStatus.MATCH
    assert result.mismatches == {}


def test_same_year_wrong_day_is_a_date_mismatch(official):
    result = CitationMatcher().match(
        claim(claimed_date=date(2009, 4, 3), claimed_year=2009), official
    )
    assert result.mismatches == {"date": {"claimed": "2009-04-03", "official": "2009-04-02"}}


def test_year_only_claim_is_checked_against_the_year(official):
    assert CitationMatcher().match(claim(claimed_year=2009), official).status is MatchStatus.MATCH
    assert CitationMatcher().match(claim(claimed_year=2008), official).status is MatchStatus.MISMATCH


def test_wrong_party_names_are_a_title_mismatch(official):
    result = CitationMatcher().match(claim(title="Ople v. Torres"), official)
    assert result.status is MatchStatus.MISMATCH
    assert set(result.mismatches) == {"title"}
    assert result.mismatches["title"]["claimed"] == "Ople v. Torres"


def test_shorthand_title_matches_the_long_official_title(official):
    # official: "REVIEW CENTER ASSOCIATION OF THE PHILIPPINES, Petitioner, vs. EXECUTIVE SECRETARY EDUARDO ERMITA ..."
    assert CitationMatcher().match(claim(title="Review Center v Ermita"), official).status is MatchStatus.MATCH


def test_different_gr_number_is_reported(official):
    result = CitationMatcher().match(claim(gr_number=GrNumber("180047")), official)
    assert result.mismatches["gr_no"] == {"claimed": "180047", "official": "180046"}


def test_nothing_to_compare_means_match_not_failure(official):
    result = CitationMatcher().match(claim(), official)
    assert result.status is MatchStatus.MATCH
    assert result.unverified == []
