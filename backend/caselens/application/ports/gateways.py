"""Ports for things the application needs from the outside world.

Use cases depend on these abstractions; infrastructure provides the implementations.
"""
from abc import ABC, abstractmethod

from caselens.domain.entities import Case
from caselens.domain.finished_reviewer import FinishedReviewer
from caselens.domain.value_objects import GrNumber


class DocumentTextExtractor(ABC):
    """Turns the bytes of one file format into plain text."""

    @abstractmethod
    def supports(self, filename: str) -> bool:
        """True if this extractor can read a file with this name."""

    @abstractmethod
    def extract(self, data: bytes) -> str:
        """Return the document text. Raises DocumentExtractionError on failure."""


class ReviewerBlockReader(ABC):
    """Reads an uploaded reviewer as its paragraphs (not one long text), so a digest box can be placed after the
    paragraph that cites a case."""

    @abstractmethod
    def supports(self, filename: str) -> bool: ...

    @abstractmethod
    def blocks(self, filename: str, data: bytes) -> list[str]:
        """The paragraphs in reading order. For a Word file, exactly the file's own paragraphs (empty ones included,
        so a position here is a position in the file)."""


class ReviewerDocumentExporter(ABC):
    @abstractmethod
    def export(self, reviewer: "FinishedReviewer", original: bytes | None) -> bytes:
        """The finished reviewer as a Word (.docx) file."""


class CaseDocumentExporter(ABC):
    @abstractmethod
    def export(self, cases: list[Case]) -> bytes:
        """The full decisions (text, footnotes and opinions exactly as the Court printed them) as one Word (.docx) file."""


class UploadedFileReader(ABC):
    """Reads any supported uploaded file; picks the format by filename."""

    @abstractmethod
    def read(self, filename: str, data: bytes) -> str:
        """Raises UnsupportedDocumentError or DocumentExtractionError."""


class CaseLocator(ABC):
    """Finds where the official documents for a G.R. number live."""

    @abstractmethod
    def locate(self, gr_no: GrNumber, claimed_year: int | None) -> list[str]:
        """Official URLs for this G.R. number, primary decision first; [] if none found.

        `claimed_year` is only a hint: a student's year may be wrong.
        """


class CaseFetcher(ABC):
    """Downloads the raw page for an official URL."""

    @abstractmethod
    def fetch(self, url: str) -> str:
        """Raises InvalidSourceUrlError, CaseNotFoundError or SourceUnavailableError."""


class CaseParser(ABC):
    """Turns one official source page into a `Case`."""

    @abstractmethod
    def parse(self, html: str, source_url: str) -> Case:
        """Raises CaseParseError if the page is not in the expected shape."""


class JobQueue(ABC):
    """Hands slow work (network crawling) to a background worker."""

    @abstractmethod
    def enqueue_resolve_upload(self, upload_id: int) -> None: ...

    @abstractmethod
    def enqueue_fetch_case(self, gr_no: str, year: int | None) -> None: ...

    @abstractmethod
    def enqueue_build_digest(self, digest_id: int, keys: list[str] | None = None) -> None:
        """Fill in a digest in the background (the AI answers take 10-20 seconds each). `keys` limits
        the work to those answer fields; None means everything still pending."""

    @abstractmethod
    def enqueue_bulk_item(self, item_id: int) -> None:
        """Resolve one item of a bulk upload (read Lawphil, find its main case) in the background. Runs once per item."""

    @abstractmethod
    def enqueue_case_digest(self, digest_id: int) -> None:
        """Write one case digest (a case and its topic scope) in the background (a few minutes of AI work). Asking twice runs it once."""

    @abstractmethod
    def enqueue_case_question(self, question_id: int) -> None:
        """Answer a question asked about a case, in the background (a few seconds of AI work)."""

    @abstractmethod
    def enqueue_refresh_catalog(self) -> bool:
        """Re-read the newest monthly lists. False if one was already queued today."""

    @abstractmethod
    def enqueue_build_catalog(self, first_year: int) -> bool:
        """Start reading Lawphil's monthly lists in the background. False if a build is
        already running (only one at a time)."""
