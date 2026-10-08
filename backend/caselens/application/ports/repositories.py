"""Persistence ports. Small and separate on purpose (Interface Segregation):
a class that only needs the month-index cache is never forced to know about cases."""
from abc import ABC, abstractmethod

from collections.abc import Sequence

from caselens.domain.entities import Case, CaseSummary, Upload, UploadSummary
from caselens.domain.subjects import Subject, SubjectCount
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
    def search(
        self, query: str | None, limit: int, offset: int, subject_id: int | None = None, no_subject: bool = False
    ) -> tuple[list[CaseSummary], int]:
        """MAIN cases (one row per case), newest decision first, plus the total that match.

        `query` matches part of the case name or the start of the G.R. number. `subject_id` keeps the cases carrying that tag;
        `no_subject` keeps the cases with no tag yet."""

    @abstractmethod
    def find_overlapping(self, numbers: Sequence[str]) -> list[CaseSummary]:
        """Every stored page (main or related) that prints any of these G.R. numbers, oldest first, with its numbers and main case."""

    @abstractmethod
    def set_main_case(self, case_ids: Sequence[int], main_case_id: int | None) -> None:
        """Point these pages at a main case (None: make them main cases themselves)."""

    @abstractmethod
    def add_subjects(self, case_id: int, subject_ids: Sequence[int], source: str) -> None:
        """Add these tags to a case; tags it already has stay as they are (never removed, never changed)."""

    @abstractmethod
    def set_subjects(self, case_id: int, subject_ids: Sequence[int], source: str) -> None:
        """Make these exactly the case's tags (an empty list clears them)."""

    @abstractmethod
    def subject_counts(self) -> list[SubjectCount]:
        """How many MAIN cases carry each tag (a case with two tags counts under both), plus those with none (subject_id None)."""


class SubjectRepository(ABC):
    @abstractmethod
    def list(self) -> list[Subject]:
        """Every subject, in the order the library shows them."""

    @abstractmethod
    def get(self, subject_id: int) -> Subject | None: ...


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

    def rollback(self) -> None:
        """Drop what was not committed (after a failed write that should not stop the operation)."""
