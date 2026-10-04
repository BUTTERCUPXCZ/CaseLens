from caselens.domain.services.reviewer_placement import CitationPlacer, CitationRef, normalise

BLOCKS = [
    "PART NINE: LEGISLATIVE DEPARTMENT",
    "See Review Center v Ermita, GR no 180046 (April 2, 2010), and also People v. Marilao, G.R. No. 71681.",
    "Explanation: the ruling in G.R. No. 180046 again.",
    "",
]


def place(*refs):
    return CitationPlacer().place(BLOCKS, list(refs))


def test_the_box_goes_after_the_first_paragraph_that_cites_the_case():
    result = place(CitationRef(1, "GR no 180046", 10))
    assert result.after_block == {1: [1]} and result.unplaced == []


def test_two_cases_cited_in_one_paragraph_keep_their_order():
    result = place(CitationRef(1, "GR no 180046", 10), CitationRef(2, "G.R. No. 71681", 11))
    assert result.after_block == {1: [1, 2]}


def test_a_case_cited_again_later_gets_one_box_at_its_first_citation():
    result = place(CitationRef(1, "GR no 180046", 10), CitationRef(2, "G.R. No. 180046", 10))
    assert result.after_block == {1: [1]} and result.unplaced == []


def test_a_citation_that_matched_no_decision_gets_no_box():
    result = place(CitationRef(1, "GR no 180046", None))
    assert result.after_block == {} and result.unplaced == []


def test_a_citation_found_in_no_paragraph_is_reported_not_lost():
    result = place(CitationRef(1, "G.R. No. 999999", 10))
    assert result.after_block == {} and result.unplaced == [1]


def test_zero_width_marks_and_odd_spacing_do_not_hide_a_citation():
    blocks = ["See GR​  no 180046 here"]
    assert CitationPlacer().place(blocks, [CitationRef(1, "GR no 180046", 5)]).after_block == {0: [1]}


def test_normalise_is_case_and_space_insensitive():
    assert normalise("  GR​ NO \n 180046 ") == "gr no 180046"


def test_a_line_that_is_only_the_header_of_the_students_own_digest_is_not_a_place_the_case_is_cited():
    blocks = [
        "Digest 1: Facts and Doctrine",
        "Review Center v Ermita, 538 SCRA 428, GR no 180046 (April 2, 2010)",
        "Facts:",
        "Following a major nursing exam leakage scandal...",
    ]
    result = CitationPlacer().place(blocks, [CitationRef(1, "GR no 180046", 10)])
    assert result.after_block == {} and result.unplaced == [1]  # goes to the end, not into the middle of their box


def test_a_normal_paragraph_that_starts_with_the_citation_still_counts():
    blocks = ["Review Center v Ermita, GR no 180046 held that the order is void.", "Explanation: more text."]
    assert CitationPlacer().place(blocks, [CitationRef(1, "GR no 180046", 10)]).after_block == {0: [1]}
