from datetime import date
from pathlib import Path

from caselens.domain.services.citation_extractor import GrCitationExtractor
from caselens.infrastructure.extraction.pdf_extractor import PdfTextExtractor

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def test_sample_pdf_yields_exactly_the_one_known_citation():
    """EXPECTED.md: one citation line (printed twice): GR 180046, claimed April 2, 2010."""
    text = PdfTextExtractor().extract((FIXTURES / "sample_case.pdf").read_bytes())
    citations = GrCitationExtractor().extract(text)

    assert len(citations) == 1
    citation = citations[0]
    assert str(citation.gr_number) == "180046"
    assert citation.claimed_year == 2010
    assert citation.claimed_date == date(2010, 4, 2)
    assert citation.title == "Review Center v Ermita"
    assert citation.reporter == "538 SCRA 428"
