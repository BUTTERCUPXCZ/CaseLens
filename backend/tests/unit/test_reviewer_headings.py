import pytest

from caselens.domain.services.reviewer_headings import ReviewerHeadings

H = ReviewerHeadings()


@pytest.mark.parametrize(
    ("text", "position", "level"),
    [
        ("Sample case", 0, 1),
        ("Constitutional Law Reviewer", 0, 1),
        ("PART NINE: LEGISLATIVE DEPARTMENT - Article VI 1987 Constitution", 1, 1),
        ("I. Legislative power Section 1:", 2, 2),
        ("II. Reclassification of positions", 5, 2),
        ("A. General Plenary powers", 8, 3),
        ("2. Reclassification of positions", 9, 3),
        ("Digest 1: Facts and Doctrine", 3, 3),
        ("TOPIC EXPLAINED:", 4, 1),
    ],
)
def test_headings_of_the_students_own_reviewer_are_recognised(text, position, level):
    assert H.level(text, position) == level


@pytest.mark.parametrize(
    "text",
    [
        "Section 1: The legislative power shall be vested in the Congress of the Philippines which shall consist of a Senate.",
        "Explanation: Legislative power is the authority under the Constitution to make, alter, and repeal laws.",
        "1. Amending the RIRR by excluding independent review centers from the coverage of the CHED;",
        "See Review Center v Ermita, 538 SCRA 428, GR no 180046 (April 2, 2010).",
        "The petition is granted.",
        "",
    ],
)
def test_sentences_and_list_points_are_body_text(text):
    assert H.level(text, 6) is None


def test_a_long_line_is_never_a_heading():
    assert H.level("A. " + "word " * 40, 3) is None


def test_digests_the_student_already_wrote_in_the_file_are_counted():
    blocks = ["Sample case", "Digest 1: Facts and Doctrine", "Review Center v Ermita ...", "Digest 2: Facts Issue and Ruling and Doctrine Sub section"]
    assert H.own_digest_count(blocks) == 2
    assert H.own_digest_count(["Section 1: The legislative power ...", "A. General Plenary powers"]) == 0


def test_the_real_sample_pdf_is_recognised_as_already_having_digests():
    from caselens.infrastructure.extraction.block_reader import PdfBlockReader
    from tests.helpers import FIXTURES

    blocks = PdfBlockReader().blocks("sample_case.pdf", (FIXTURES / "sample_case.pdf").read_bytes())
    assert H.own_digest_count(blocks) == 2
