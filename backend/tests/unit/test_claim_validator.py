"""The code checks that decide which written digest sentences a second model must still judge. Real passages from Marcos v. Manglapus."""
import pytest

from caselens.domain.digest import AnswerSentence, SourcePassage
from caselens.domain.digest_v2 import Section
from caselens.domain.services.claim_validator import ClaimStatus, ClaimValidator

SOURCES = {
    s.id: s
    for s in (
        SourcePassage("C1", "FERDINAND E. MARCOS, petitioners, vs. HONORABLE RAUL MANGLAPUS, respondents. G.R. No. 88211 September 15, 1989 EN BANC"),
        SourcePassage("P6", "In February 1986, Ferdinand E. Marcos was deposed from the presidency via the non-violent people power revolution and forced into exile."),
        SourcePassage("P9", "The President has decided to bar the Marcoses from returning, citing dire consequences to the nation's stability."),
        SourcePassage("P10", "Petitioners contend that the President is without power to impair their liberty of abode and their right to travel."),
        SourcePassage("P20", "We hold that the President did not act arbitrarily in barring the return of the Marcoses."),
        SourcePassage("O2.1", "(Cruz, J., dissenting) It is my belief that the petitioner, as a citizen, is entitled to return to his country."),
    )
}


def classify(text, cites, section=Section.FACTS, coverage_min=0.6):
    return ClaimValidator(coverage_min).classify(AnswerSentence(text, tuple(cites)), SOURCES, section)


def test_a_plain_sentence_in_the_cited_paragraphs_own_words_passes():
    assert classify("In February 1986, Marcos was deposed from the presidency and forced into exile.", ["P6"]).status is ClaimStatus.PASS


def test_an_honest_not_stated_needs_no_cite_but_a_claim_without_one_is_invalid():
    assert classify("The decision does not say who the justices were.", []).status is ClaimStatus.PASS
    check = classify("The President was right.", [])
    assert check.status is ClaimStatus.INVALID and check.reason == "no source cited"


@pytest.mark.parametrize(
    ("text", "cites", "reason"),
    [
        ("Marcos was deposed.", ["P99"], "does not exist"),
        ("Marcos was deposed.", ["paragraph 6"], "not a passage id"),
        ("Marcos was deposed in 1999.", ["P6"], "1999"),
        ("Justice Roxas agreed with the exile.", ["P6"], "Roxas"),
        ("The case is G.R. No. 88212.", ["C1"], "88212"),
    ],
)
def test_what_cannot_be_in_the_decision_is_invalid(text, cites, reason):
    check = classify(text, cites)
    assert check.status is ClaimStatus.INVALID and reason in check.reason


@pytest.mark.parametrize(
    ("text", "cites", "reason"),
    [
        ("Marcos was deposed from the presidency in 1989.", ["P6"], "number 1989"),  # 1989 is in the caption, not in P6
        ("The President, through Manglapus, decided to bar the Marcoses from returning.", ["P9"], "Manglapus"),
        ("The President always has power to bar the Marcoses from returning.", ["P9"], "'always'"),
        ("The President has not decided to bar the Marcoses from returning.", ["P9"], "negation"),
        ("The Court held that the President is without power to impair their liberty of abode.", ["P10"], "party's argument"),
        ("The revolution was a bloodless coup supported by foreign governments.", ["P6"], "of its words"),
    ],
)
def test_what_only_a_reader_of_meaning_can_judge_is_suspicious(text, cites, reason):
    check = classify(text, cites)
    assert check.status is ClaimStatus.SUSPICIOUS and reason in check.reason


def test_the_court_s_own_holding_is_not_mistaken_for_an_argument():
    assert classify("The Court held that the President did not act arbitrarily in barring the return of the Marcoses.", ["P20"]).status is ClaimStatus.PASS


def test_a_dissent_must_cite_the_named_justice_s_own_opinion():
    assert classify("Cruz, J.: The petitioner, as a citizen, is entitled to return to his country.", ["O2.1"], Section.DISSENTS).status is ClaimStatus.PASS
    check = classify("Gutierrez, J.: The petitioner, as a citizen, is entitled to return to his country.", ["O2.1", "C1"], Section.DISSENTS)
    assert check.status is not ClaimStatus.PASS


def test_the_word_share_needed_to_pass_is_a_setting():
    text = "The President barred the Marcoses, invoking grave threats to national security."
    assert classify(text, ["P9"], coverage_min=0.9).status is ClaimStatus.SUSPICIOUS
    assert classify(text, ["P9"], coverage_min=0.2).status is ClaimStatus.PASS
