import pytest

from caselens.infrastructure.ai.gemini_answerer import strip_inline_citations


@pytest.mark.parametrize(
    ("raw", "clean", "ids"),
    [
        ("EO 566 directed the CHED to regulate review centers [P11].", "EO 566 directed the CHED to regulate review centers.", ["P11"]),
        ("The Court declared both void (P101, P105).", "The Court declared both void.", ["P101", "P105"]),
        ("It was void [P12] and unconstitutional [S1].", "It was void and unconstitutional.", ["P12", "S1"]),
        ("The petition was granted P132.", "The petition was granted.", ["P132"]),
        ("The Court held it void.", "The Court held it void.", []),
        ("EO 566 and RIRR are void for P.D. reasons.", "EO 566 and RIRR are void for P.D. reasons.", []),
    ],
)
def test_ids_are_taken_out_of_the_sentence_and_kept_as_citations(raw, clean, ids):
    assert strip_inline_citations(raw) == (clean, ids)
