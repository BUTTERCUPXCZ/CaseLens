import pymupdf

from caselens.application.ports.gateways import DocumentTextExtractor
from caselens.domain.errors import DocumentExtractionError


class PdfTextExtractor(DocumentTextExtractor):
    """Reads text-based PDFs. Scanned (image-only) PDFs are rejected, not OCR'd."""

    def supports(self, filename: str) -> bool:
        return filename.lower().endswith(".pdf")

    def extract(self, data: bytes) -> str:
        try:
            with pymupdf.open(stream=data, filetype="pdf") as doc:
                text = "\n".join(page.get_text() for page in doc)
        except Exception as exc:  # pymupdf raises several unrelated types
            raise DocumentExtractionError(f"Cannot read PDF: {exc}") from exc
        if not text.strip():
            raise DocumentExtractionError(
                "PDF has no extractable text (scanned image PDFs are not supported)."
            )
        return text
