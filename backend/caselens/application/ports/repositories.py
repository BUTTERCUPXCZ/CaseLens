"""Persistence ports. Small and separate on purpose (Interface Segregation):
a class that only needs the month-index cache is never forced to know about cases."""
from abc import ABC, abstractmethod

from caselens.domain.entities import Case, CaseSummary, Upload, UploadSummary
from caselens.domain.value_objects import GrNumber


class MonthIndexRepository(ABC):
    """Cache of Lawphil month-index pages so each is downloaded once."""

    @abstractmethod
    def get(self, url: str) -> list[str] | None:
        """Cached case-page URLs for this index page, or None if never cached."""

    @abstractmethod
    def save(self, url: str, case_urls: list[str]) -> None:
        """Store (or replace) the case-page URLs for this index page."""


class CaseRepository(ABC):
    @abstractmethod
    def add(self, case: Case) -> Case:
        """Store a new case and return it with its id. Raises DuplicateCaseError
        if the source URL is already stored."""

    @abstractmethod
    def get(self, case_id: int) -> Case | None: ...

    @abstractmethod
    def get_by_source_url(self, url: str) -> Case | None: ...

    @abstractmethod
    def find_by_gr_no(self, gr_no: GrNumber) -> list[Case]:
        """All stored documents for this G.R. number, oldest first."""

    @abstractmethod
    def summaries(self, case_ids: list[int]) -> dict[int, CaseSummary]:
        """A light summary (name, date, ponente, ruling, official URL) for each id, without
        loading the large case bodies."""

    @abstractmethod
    def outdated(self, current_parser_version: int) -> list[tuple[int, str, str]]:
        """(id, source_url, raw_html) of cases parsed by an older parser version."""

    @abstractmethod
    def with_damaged_text(self) -> list[tuple[int, str]]:
        """(id, source_url) of cases whose stored page contains the Unicode replacement
        character: text that was damaged when it was downloaded."""

    @abstractmethod
    def update_content(self, case_id: int, parsed: Case) -> None:
        """Replace a stored case's parsed content in place; its id and any uploads
        pointing at it stay valid."""

    @abstractmethod
    def search(self, query: str | None, limit: int, offset: int) -> tuple[list[CaseSummary], int]:
        """Stored cases, newest decision first, plus the total that match.

        `query` matches part of the case name or the start of the G.R. number."""


class UploadRepository(ABC):
    @abstractmethod
    def add(self, upload: Upload) -> Upload:
        """Store a new upload with its citations; returns it with ids filled in."""

    @abstractmethod
    def get(self, upload_id: int) -> Upload | None: ...

    @abstractmethod
    def get_file_data(self, upload_id: int) -> bytes | None:
        """The original uploaded file, or None (uploads from before it was kept)."""

    @abstractmethod
    def save(self, upload: Upload) -> None:
        """Persist changes to the upload's status and its citations' results."""

    @abstractmethod
    def delete(self, upload_id: int) -> bool:
        """Remove an upload with its citations, original file and digests. The cases it cited are kept. False if it does not exist."""

    @abstractmethod
    def list_recent(self, limit: int) -> list[UploadSummary]:
        """Newest uploads first, each with how many of its citations are in each state."""


class UnitOfWork(ABC):
    """Marks the end of a business operation: everything before it is saved together."""

    @abstractmethod
    def commit(self) -> None: ...
