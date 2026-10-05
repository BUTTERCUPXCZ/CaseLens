"""Reading what a student gives to Bulk: a pasted list of G.R. numbers, and the caption of a decision file (never the cases it cites)."""
import pytest

from caselens.domain.services.gr_list_parser import GrListParser
from caselens.domain.services.main_case_identifier import MainCaseIdentifier
from tests.helpers import digest_paragraphs


def numbers(text):
    return [(e.gr_no.value if e.gr_no else None, e.year) for e in GrListParser().parse(text)]


def test_a_pasted_list_is_read_line_by_line_whatever_its_labels():
    assert numbers("88211\nG.R. No. 148263\nGR no 180046 (2009)\nL-17169") == [("88211", None), ("148263", None), ("180046", 2009), ("L-17169", None)]


def test_commas_semicolons_and_ampersands_separate_numbers_and_a_joint_listing_becomes_its_numbers():
    assert numbers("G.R. Nos. 148263, 148271 & 148272; 88211") == [("148263", None), ("148271", None), ("148272", None), ("88211", None)]


def test_what_is_not_a_g_r_number_is_kept_so_the_student_can_see_it_was_skipped():
    entries = GrListParser().parse("banana\n12\n88211")
    assert [(e.raw, e.gr_no is not None) for e in entries] == [("banana", False), ("12", False), ("88211", True)]


def test_blank_lines_and_an_empty_paste_give_nothing():
    assert GrListParser().parse("\n\n  \n") == [] and GrListParser().parse("") == []


@pytest.mark.parametrize(
    ("name", "main", "numbers_printed"),
    [
        ("gr_180046_2009.html", "180046", ["180046"]),
        ("gr_148263_2009.html", "148263", ["148263", "148271", "148272"]),  # a joint decision prints "148263 and 148271-72"
        ("gr_88211_1989.html", "88211", ["88211"]),
        ("gr_211972_2015.html", "211972", ["211972", "212045"]),
    ],
)
def test_a_decision_is_identified_by_its_caption_whatever_it_cites(name, main, numbers_printed):
    text = "\n".join(digest_paragraphs(name))
    found = MainCaseIdentifier().identify(text)
    assert found.problem is None and found.main.value == main and [n.value for n in found.gr_numbers] == numbers_printed


def test_the_cases_a_decision_cites_are_never_read_as_the_case():
    import re

    text = "\n".join(digest_paragraphs("gr_173931_2009.html"))
    assert len(re.findall(r"G\.?R\.? Nos?\.?\s*L?-?\d+", text)) >= 3  # the decision cites other cases by G.R. number
    assert [n.value for n in MainCaseIdentifier().identify(text).gr_numbers] == ["173931"]


def test_the_year_printed_beside_the_number_is_a_hint():
    assert MainCaseIdentifier().identify("EN BANC\nG.R. No. 88211 September 15, 1989\nMARCOS v MANGLAPUS").year == 1989


def test_a_file_whose_first_lines_have_no_caption_number_is_unreadable_not_guessed():
    found = MainCaseIdentifier().identify("My reviewer notes\nSee G.R. No. 12345 for the rule.\nAlso GR 99999.")
    assert found.main is None and "could not read" in found.problem and found.gr_numbers == ()
    assert MainCaseIdentifier().identify("").problem is not None


def test_a_digest_whose_citation_line_puts_the_reporter_first_is_still_its_case():
    # The client's sample digest (Marcos_v_Manglapus_Case_Digest.docx), its first lines exactly.
    text = "CASE DIGEST\nMarcos v. Manglapus\n177 SCRA 668, G.R. No. 88211, September 15, 1989 (En Banc)\nTopic: Constitutional Law"
    found = MainCaseIdentifier().identify(text)
    assert [n.value for n in found.gr_numbers] == ["88211"] and found.year == 1989


def test_a_sentence_that_mentions_a_number_after_other_words_is_still_not_the_case():
    assert MainCaseIdentifier().identify("Notes\nIn 177 SCRA 668 the Court cited G.R. No. 12345.").problem is not None
    assert MainCaseIdentifier().identify("See 177 SCRA 668, G.R. No. 12345.").problem is not None


def test_a_reviewer_is_the_cases_under_its_digest_boxes_each_once_from_the_clients_real_file():
    from caselens.domain.services.main_case_identifier import ReviewerCaseFinder
    from caselens.infrastructure.extraction.pdf_extractor import PdfTextExtractor
    from tests.helpers import FIXTURES

    text = PdfTextExtractor().extract((FIXTURES / "sample_case.pdf").read_bytes())
    found = ReviewerCaseFinder().find(text if isinstance(text, str) else text.text)
    assert [(c.gr_no.value, c.title, c.reporter) for c in found] == [("180046", "Review Center v Ermita", "538 SCRA 428")]  # boxed twice, one case


def test_a_reviewer_with_several_boxes_gives_each_case_and_a_case_only_mentioned_is_not_read():
    from caselens.domain.services.main_case_identifier import ReviewerCaseFinder

    text = (
        "Notes on legislative power. See G.R. No. 111111 for the old rule.\n"
        "Digest 1: Facts and Doctrine\nReview Center v Ermita, 538 SCRA 428, GR no 180046 (April 2, 2009)\nFacts:\n"
        "Digest 2: Facts, Issue, Ruling\nTagaro v. Garcia, G.R. No. 173931, April 2, 2009\nFacts:\n"
        "Digest 3: Doctrine\nReview Center v Ermita, 538 SCRA 428, GR no 180046 (April 2, 2009)\n"
    )
    assert [c.gr_no.value for c in ReviewerCaseFinder().find(text)] == ["180046", "173931"]
