from datetime import date

import pytest

from caselens.domain.services.citation_extractor import GrCitationExtractor
from caselens.domain.value_objects import GrNumber


@pytest.fixture
def extractor() -> GrCitationExtractor:
    return GrCitationExtractor()


def numbers(citations) -> list[str]:
    return [str(c.gr_number) for c in citations]


@pytest.mark.parametrize(
    "text",
    [
        "GR no 180046",
        "G.R. No. 180046",
        "G.R. No 180046",
        "g.r. no. 180046",
        "GR No.: 180046",
        "see G.R. 180046 for details",
    ],
)
def test_single_number_formats(extractor, text):
    assert numbers(extractor.extract(text)) == ["180046"]


@pytest.mark.parametrize(
    "text, expected",
    [
        ("G.R. Nos. 180046 and 180047", ["180046", "180047"]),
        ("G.R. Nos. 192935 & 193036", ["192935", "193036"]),
        ("G.R. Nos. 176951, 177499 and 178056", ["176951", "177499", "178056"]),
    ],
)
def test_multiple_numbers(extractor, text, expected):
    assert numbers(extractor.extract(text)) == expected


def test_old_style_l_prefix(extractor):
    assert numbers(extractor.extract("G.R. No. L-12345 (1960)")) == ["L-12345"]


@pytest.mark.parametrize(
    "text",
    [
        "Republic Act No. 8981 was enacted",
        "Executive Order No. 566",
        "page 180046 of the report",
        "GROUND 180046",
        "Section 7 of RA 8981",
    ],
)
def test_no_false_positives(extractor, text):
    assert extractor.extract(text) == []


def test_year_after_comma_is_not_a_second_number(extractor):
    result = extractor.extract("G.R. No. 180046, 2010")
    assert numbers(result) == ["180046"]


@pytest.mark.parametrize(
    "text, expected_date, expected_year",
    [
        ("GR no 180046 (April 2, 2010)", date(2010, 4, 2), 2010),
        ("G.R. No. 180046, April 2, 2009", date(2009, 4, 2), 2009),
        ("G.R. No. 180046, 2 April 2009", date(2009, 4, 2), 2009),
        ("G.R. No. 180046 (2009)", None, 2009),
        ("G.R. No. 180046", None, None),
        ("G.R. No. 180046 (February 31, 2010)", None, 2010),
    ],
)
def test_claimed_date_and_year(extractor, text, expected_date, expected_year):
    (citation,) = extractor.extract(text)
    assert citation.claimed_date == expected_date
    assert citation.claimed_year == expected_year


def test_title_and_reporter_from_citation_line(extractor):
    text = "Digest 1\nReview Center v Ermita, 538 SCRA 428, GR no 180046 (April 2, 2010)\nFacts:"
    (citation,) = extractor.extract(text)
    assert citation.gr_number == GrNumber("180046")
    assert citation.title == "Review Center v Ermita"
    assert citation.reporter == "538 SCRA 428"
    assert citation.claimed_year == 2010


def test_repeated_identical_citations_are_deduplicated(extractor):
    line = "Review Center v Ermita, 538 SCRA 428, GR no 180046 (April 2, 2010)"
    assert len(extractor.extract(f"{line}\n...\n{line}")) == 1


def test_zero_width_characters_do_not_break_matching(extractor):
    assert numbers(extractor.extract("GR​ no 180046​")) == ["180046"]


def test_invalid_gr_number_value_object():
    with pytest.raises(ValueError):
        GrNumber("12")
