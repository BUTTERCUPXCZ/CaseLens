import io
import re

import docx
import pymupdf

from caselens.application.ports.gateways import ReviewerBlockReader
from caselens.domain.errors import DocumentExtractionError, UnsupportedDocumentError

_ZERO_WIDTH = dict.fromkeys(map(ord, "​‌‍﻿"), None)


_SENTENCE_END = (".", "?", "!", ":", ";", ")")
_BULLET = re.compile(r"^(?:[•▪◦\-*–]|\(?[a-z0-9]{1,2}[.)])\s")


def _is_label(text: str) -> bool:
    """A short all-capitals line such as "TOPIC EXPLAINED:" or "WHY THIS CASE MATTERS": a heading, never part of a sentence."""
    letters = [c for c in text if c.isalpha()]
    return len(letters) >= 3 and text.upper() == text and len(text.split()) <= 8


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.translate(_ZERO_WIDTH).replace("\u00a0", " ")).strip()


def paragraphs_of_block(block: str, has_paragraph_marks: bool) -> list[str]:
    """One PDF text block as the paragraphs the student wrote, not one run-together line.

    A PDF stores a paragraph as several visual lines. Google Docs and Word mark the last line of a paragraph with a
    hidden zero-width character; that is the reliable signal. A PDF without it falls back to: an all-capitals line
    is a heading, a list marker starts a new paragraph, and a line that ends a sentence before a capital letter does too.
    """
    paragraphs: list[str] = []
    current = ""
    for raw in block.split("\n"):
        line = _clean(raw)
        if not line:
            continue
        if current and (_is_label(current) or _is_label(line) or _BULLET.match(line)):
            paragraphs.append(current)
            current = ""
        if current and not has_paragraph_marks and current.endswith(_SENTENCE_END) and (line[0].isupper() or line[0].isdigit()):
            paragraphs.append(current)
            current = ""
        current = f"{current} {line}" if current else line
        if raw.rstrip().endswith("\u200b") and has_paragraph_marks:  # the hidden end-of-paragraph mark
            paragraphs.append(current)
            current = ""
    if current:
        paragraphs.append(current)
    return paragraphs


class PdfBlockReader(ReviewerBlockReader):
    """A PDF's text as the student's paragraphs, in the order the file stores them."""

    def supports(self, filename: str) -> bool:
        return filename.lower().endswith(".pdf")

    def blocks(self, filename: str, data: bytes) -> list[str]:
        try:
            with pymupdf.open(stream=data, filetype="pdf") as document:
                raw = [block[4] for page in document for block in page.get_text("blocks") if block[6] == 0]
        except Exception as exc:
            raise DocumentExtractionError(f"Cannot read PDF: {exc}") from exc
        marked = any("\u200b" in text for text in raw)
        return [paragraph for text in raw for paragraph in paragraphs_of_block(text, marked)]


class DocxBlockReader(ReviewerBlockReader):
    """A Word file's own paragraphs, empty ones included, so the position of a paragraph here is its position in the file."""

    def supports(self, filename: str) -> bool:
        return filename.lower().endswith(".docx")

    def blocks(self, filename: str, data: bytes) -> list[str]:
        try:
            document = docx.Document(io.BytesIO(data))
        except Exception as exc:
            raise DocumentExtractionError(f"Cannot read DOCX: {exc}") from exc
        return [paragraph.text for paragraph in document.paragraphs]


class CompositeBlockReader(ReviewerBlockReader):
    def __init__(self, readers: list[ReviewerBlockReader]) -> None:
        self._readers = readers

    def supports(self, filename: str) -> bool:
        return any(reader.supports(filename) for reader in self._readers)

    def blocks(self, filename: str, data: bytes) -> list[str]:
        for reader in self._readers:
            if reader.supports(filename):
                return reader.blocks(filename, data)
        raise UnsupportedDocumentError(f"Cannot read '{filename}': only PDF and Word (.docx) files are supported.")
