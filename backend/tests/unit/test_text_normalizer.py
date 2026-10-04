import pytest

from caselens.domain.services.text_normalizer import TextNormalizer


@pytest.fixture
def normalizer() -> TextNormalizer:
    return TextNormalizer.default()


def test_strips_zero_width_characters(normalizer):
    assert normalizer.normalize("Sample​ case​") == "Sample case"


@pytest.mark.parametrize("junk", ["1awphi1", "1avvphi1"])
def test_strips_lawphil_watermark(normalizer, junk):
    assert normalizer.normalize(f"Congress.{junk} The issue") == "Congress. The issue"


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("before the Regional Trial Court.21 The alleged", "before the Regional Trial Court. The alleged"),
        ("two Board of Nursing members.3 On 19 June", "two Board of Nursing members. On 19 June"),
        ("In Ople v. Torres,33 the Court declared", "In Ople v. Torres, the Court declared"),
        ("Executive Order No. 292 (EO 292),29 particularly", "Executive Order No. 292 (EO 292), particularly"),
    ],
)
def test_strips_glued_footnote_markers(normalizer, raw, expected):
    assert normalizer.normalize(raw) == expected


@pytest.mark.parametrize(
    "text",
    [
        "Republic Act No. 8981 was enacted",   # number after space, not glued
        "rate of 3.5 percent",                  # decimal, preceded by a digit
        "from ₱400,000 to ₱20,000",   # thousands separators
    ],
)
def test_does_not_damage_real_numbers(normalizer, text):
    assert normalizer.normalize(text) == text


def test_unifies_typography_and_whitespace(normalizer):
    assert normalizer.normalize("“Plenary” power –  here") == '"Plenary" power - here'
