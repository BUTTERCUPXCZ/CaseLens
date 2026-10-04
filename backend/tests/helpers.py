from pathlib import Path

from caselens.domain.entities import Case
from caselens.infrastructure.lawphil.html_decoding import decode_html
from caselens.infrastructure.lawphil.html_parser import LawphilCaseParser

FIXTURES = Path(__file__).resolve().parent / "fixtures"
OFFICIAL_URL = "https://lawphil.net/judjuris/juri2009/apr2009/gr_180046_2009.html"


def read_fixture_html(name: str) -> str:
    """A saved Lawphil page, decoded the way production decodes it (windows-1252, not lossy UTF-8)."""
    return decode_html((FIXTURES / name).read_bytes(), "text/html")


def official_html() -> str:
    return read_fixture_html("gr_180046_2009.html")


def parse_official_case() -> Case:
    """The real GR 180046 page, parsed. Fresh object each call (id is None)."""
    return LawphilCaseParser().parse(official_html(), OFFICIAL_URL)


def sample_pdf_bytes() -> bytes:
    return (FIXTURES / "sample_case.pdf").read_bytes()


def digest_paragraphs(name: str) -> list[str]:
    """A saved decision (tests/fixtures/digest/ or tests/fixtures/) as the stored paragraphs, in order."""
    for folder in (FIXTURES / "digest", FIXTURES):
        path = folder / name
        if path.exists():
            html = decode_html(path.read_bytes(), "text/html")
            return LawphilCaseParser().parse(html, f"https://lawphil.net/x/{name}").full_text.split("\n")
    raise FileNotFoundError(name)


def parse_digest_case(name: str) -> Case:
    """A saved decision from tests/fixtures/digest/ (or tests/fixtures/) parsed into a Case, id not yet set."""
    for folder in (FIXTURES / "digest", FIXTURES):
        path = folder / name
        if path.exists():
            return LawphilCaseParser().parse(decode_html(path.read_bytes(), "text/html"), f"https://lawphil.net/x/{name}")
    raise FileNotFoundError(name)


REVIEWER_PARAGRAPHS = [
    "PART NINE: LEGISLATIVE DEPARTMENT - Article VI 1987 Constitution",
    "I. Legislative power Section 1:",
    "Section 1: The legislative power shall be vested in the Congress of the Philippines. "
    "See Review Center v Ermita, 538 SCRA 428, GR no 180046 (April 2, 2010) on the limits.",
    "Explanation: Legislative power is the authority to make laws.",
]


def reviewer_docx(paragraphs: list[str] | None = None) -> bytes:
    """A small reviewer as a real .docx file (the student's own text, no digests yet)."""
    import io

    import docx

    document = docx.Document()
    for text in paragraphs or REVIEWER_PARAGRAPHS:
        document.add_paragraph(text)
    out = io.BytesIO()
    document.save(out)
    return out.getvalue()
