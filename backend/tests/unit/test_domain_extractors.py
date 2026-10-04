"""Unit tests for the small text-reading domain services.

Strings marked (synthetic) were written for the test, not taken from Lawphil: they
check the rule itself, not a fact about the real site.
"""
import pytest

from caselens.domain.services.cited_case_extractor import CitedCaseExtractor
from caselens.domain.services.disposition_classifier import DispositionClassifier
from caselens.domain.services.statute_extractor import StatuteExtractor
from caselens.domain.value_objects import Disposition, StatuteType


@pytest.mark.parametrize(
    "text, expected",
    [
        # real, from GR 180046
        ("WHEREFORE , we GRANT the petition and the petition-in-intervention.", Disposition.GRANTED),
        # (synthetic)
        ("WHEREFORE, the petition is DENIED for lack of merit.", Disposition.DENIED),
        ("WHEREFORE, the petition is DISMISSED.", Disposition.DISMISSED),
        ("WHEREFORE, we GRANT the petition in part and DENY the rest.", Disposition.PARTIALLY_GRANTED),
        ("WHEREFORE, the petition is PARTLY GRANTED.", Disposition.PARTIALLY_GRANTED),
        ("WHEREFORE, we GRANT the petition in part.", Disposition.PARTIALLY_GRANTED),
        ("WHEREFORE, the Decision is AFFIRMED.", Disposition.AFFIRMED),
        ("WHEREFORE, the Decision is REVERSED.", Disposition.REVERSED),
        ("Wherefore, nothing in capitals here, we grant it.", Disposition.UNKNOWN),
        (None, Disposition.UNKNOWN),
    ],
)
def test_disposition(text, expected):
    assert DispositionClassifier().classify(text) is expected


def pairs(statutes):
    return [(s.statute_type, s.number) for s in statutes]


def test_statutes_all_citation_styles_seen_in_gr_180046():
    text = "Republic Act No. 8981, R.A. 7722, R.A.8981, RA 7722, Executive Order No. 292 and EO 566."
    assert pairs(StatuteExtractor().extract(text)) == [
        (StatuteType.REPUBLIC_ACT, "8981"),
        (StatuteType.REPUBLIC_ACT, "7722"),
        (StatuteType.EXECUTIVE_ORDER, "292"),
        (StatuteType.EXECUTIVE_ORDER, "566"),
    ]


def test_abbreviation_in_parentheses_after_the_full_name():
    """Real wording from GR 173931: 'Section 11 of Republic Act (R.A.) No. 7722'."""
    text = "under the authority of Section 11 of Republic Act (R.A.) No. 7722. Also Executive Order (E.O.) No. 566."
    assert pairs(StatuteExtractor().extract(text)) == [
        (StatuteType.REPUBLIC_ACT, "7722"),
        (StatuteType.EXECUTIVE_ORDER, "566"),
    ]


def test_constitution_references_in_both_orders():
    text = "under Section 1, Article VI of the 1987 Constitution and Article VII, Section 17."
    assert pairs(StatuteExtractor().extract(text)) == [
        (StatuteType.CONSTITUTION, "Art. VI, Sec. 1"),
        (StatuteType.CONSTITUTION, "Art. VII, Sec. 17"),
    ]


def test_batas_pambansa_and_commonwealth_act():  # (synthetic)
    text = "Batas Pambansa Blg. 129 and Commonwealth Act No. 141"
    assert pairs(StatuteExtractor().extract(text)) == [
        (StatuteType.BATAS_PAMBANSA, "129"),
        (StatuteType.COMMONWEALTH_ACT, "141"),
    ]


def test_plain_numbers_are_not_statutes():
    assert StatuteExtractor().extract("Section 7 of the law, 500 questions, page 292") == []


def test_cited_case_from_footnote_with_reporter_and_gr():
    cases = CitedCaseExtractor().extract(
        "", [(18, "LPBS Commercial, Inc. v. Amila , G.R. No. 147443, 11 February 2008, 544 SCRA 199.")]
    )
    assert [(c.title, c.gr_no, c.source, c.footnote_number) for c in cases] == [
        ("LPBS Commercial, Inc. v. Amila", "147443", "footnote", 18)
    ]


def test_abbreviation_period_is_kept_but_sentence_period_is_dropped():
    notes = [
        (22, "Executive Secretary v. Southwing Heavy Industries, Inc. , G.R. No. 164171, 20 February 2006."),
        (5, "Ople v. Torres."),  # (synthetic) no reporter: trailing period is sentence punctuation
    ]
    notes.append((7, "Citing Turquenza v. Hernando, et al., G.R. No. 51626, 30 April 1980."))  # real (GR 183905)
    titles = [c.title for c in CitedCaseExtractor().extract("", notes)]
    assert titles == [
        "Executive Secretary v. Southwing Heavy Industries, Inc.",
        "Ople v. Torres",
        "Turquenza v. Hernando, et al.",  # "et al." is part of the name; "Citing" is not
    ]


def test_cited_cases_split_on_citing_and_keep_comma_in_title():
    note = (
        "Liga ng mga Barangay National v. City Mayor of Manila, 465 Phil. 529, 542-543 (2004), "
        "citing People v. Cuaresma , G.R. No. 67787, 18 April 1989, 172 SCRA 415."
    )
    cases = CitedCaseExtractor().extract("", [(19, note)])
    assert [(c.title, c.gr_no, c.footnote_number) for c in cases] == [
        ("Liga ng mga Barangay National v. City Mayor of Manila", None, 19),
        ("People v. Cuaresma", "67787", 19),
    ]


def test_footnote_that_starts_with_a_capitalised_citing_keeps_only_the_case_name():
    # (synthetic) shape seen in GR 183905: a footnote beginning "Citing Turquenza v. Hernando, ..."
    cases = CitedCaseExtractor().extract("", [(34, "Citing Turquenza v. Hernando, G.R. No. 150, 1 May 2000.")])
    assert [c.title for c in cases] == ["Turquenza v. Hernando"]


def test_cited_case_from_body_strips_leading_word_and_marker():
    cases = CitedCaseExtractor().extract("In Ople v. Torres,[^33] the Court declared void", [])
    assert [(c.title, c.source, c.footnote_number) for c in cases] == [("Ople v. Torres", "body", None)]


def test_same_case_in_body_and_footnote_is_one_row_keeping_the_gr_number():
    cases = CitedCaseExtractor().extract(
        "In Ople v. Torres, the Court said", [(7, "Ople v. Torres, G.R. No. 127685, 23 July 1998.")]
    )
    assert [(c.title, c.gr_no, c.footnote_number) for c in cases] == [("Ople v. Torres", "127685", 7)]
