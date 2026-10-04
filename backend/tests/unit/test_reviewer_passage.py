from caselens.domain.services.reviewer_passage import ReviewerPassageFinder

REVIEWER = (
    "PART NINE: LEGISLATIVE DEPARTMENT - Article VI 1987 Constitution\n\n"
    "I. Legislative power Section 1:\n\n"
    "Section 1: The legislative power shall be vested in the Congress of the Philippines. "
    "See Review Center v Ermita, 538 SCRA 428, GR no 180046 (April 2, 2010) for the limits.\n\n"
    "Explanation: Legislative power is the authority to make laws."
)
CITATION = "Review Center v Ermita, 538 SCRA 428, GR no 180046 (April 2, 2010)"


def test_the_paragraph_that_cites_the_case_comes_with_its_heading():
    passage = ReviewerPassageFinder().find(REVIEWER, CITATION)
    assert passage.startswith("I. Legislative power Section 1:\nSection 1: The legislative power shall be vested")
    assert CITATION in passage and "Explanation:" not in passage


def test_a_reflowed_citation_is_still_found():
    reflowed = REVIEWER.replace("538 SCRA 428, GR no", "538 SCRA\n428, GR no")
    assert ReviewerPassageFinder().find(reflowed, CITATION) is not None


def test_a_citation_that_is_not_in_the_text_gives_nothing():
    assert ReviewerPassageFinder().find(REVIEWER, "People v. Nobody, G.R. No. 1") is None


def test_the_passage_is_cut_to_a_sane_length():
    long_text = "Heading\n\n" + ("word " * 1000) + CITATION
    assert len(ReviewerPassageFinder().find(long_text, CITATION)) <= 1200
