import pytest

from caselens.domain.digest import AnswerSentence, SourcePassage
from caselens.domain.services.answer_validator import AnswerValidator

SOURCES = {
    "P12": SourcePassage("P12", "On 8 September 2006, President Arroyo issued EO 566 which authorized the CHED to supervise review centers."),
    "P14": SourcePassage("P14", "The petitioners asked for an annulment of the RIRR and paid a registration fee of P400,000."),
    "S1": SourcePassage("S1", "Plenary power is vested in Congress."),
}


def check(text, *cites, question=""):
    return AnswerValidator().check(AnswerSentence(text, cites), SOURCES, question)


def test_a_sentence_resting_on_its_sources_passes():
    assert check("President Arroyo issued EO 566 on 8 September 2006.", "P12") is None


def test_a_sentence_with_no_source_is_refused():
    assert check("The Court agreed.") == "no source cited"


def test_a_citation_to_a_passage_that_does_not_exist_is_refused():
    assert "does not exist: P99" in check("The Court agreed.", "P99")


def test_a_number_that_is_not_in_the_cited_text_is_refused():
    assert check("The fee was P500,000.", "P14") == "number 500,000 is not in the cited text"


def test_a_number_that_is_in_the_cited_text_passes():
    assert check("The fee was P400,000.", "P14") is None


def test_the_number_must_be_in_the_passage_that_is_cited_not_in_another_one():
    assert check("EO 566 was issued in 2006.", "P14") is not None  # 566 and 2006 are in P12, not P14


def test_a_name_the_cited_text_does_not_contain_is_refused():
    assert check("The petition was filed against Ermita.", "P14") == "name 'Ermita' is not in the decision"


def test_a_name_defined_elsewhere_in_the_decision_is_allowed_even_if_not_in_the_cited_paragraph():
    # "Court of Appeals (CA)" is spelled out once; an answer citing another paragraph may spell it out too.
    sources = {**SOURCES, "P1": SourcePassage("P1", "The Decision of the Court of Appeals (CA) is affirmed.")}
    assert AnswerValidator().check(AnswerSentence("The case went up to the Appeals court.", ("P12",)), sources) is None


def test_the_first_word_of_a_sentence_is_not_treated_as_a_name():
    assert check("Petitioners asked for an annulment.", "P14") is None


def test_words_of_the_question_may_be_used():
    assert check("This concerns Congress.", "S1", question="Why does Congress matter?") is None


def test_ordinary_court_vocabulary_needs_no_citation_match():
    assert check("The Court held that plenary power is vested in Congress.", "S1") is None


def test_an_empty_sentence_is_refused():
    assert check("   ", "P12") == "empty sentence"


@pytest.mark.parametrize("text", ["It is a landmark ruling.", "It sets a vital precedent."])
def test_vague_claims_with_a_real_source_still_go_to_the_checker(text):
    # No number or name to catch here: judging whether the source SAYS this is the second AI call's job.
    assert check(text, "P12") is None
