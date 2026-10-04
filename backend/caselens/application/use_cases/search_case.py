from dataclasses import dataclass
from enum import Enum

from caselens.application.ports.catalog import CatalogRepository
from caselens.application.ports.gateways import JobQueue
from caselens.application.ports.repositories import CaseRepository
from caselens.domain.entities import Case
from caselens.domain.value_objects import GrNumber


class SearchStatus(str, Enum):
    FOUND = "found"
    PENDING = "pending"  # a background fetch was queued; ask again shortly
    NEEDS_YEAR = "needs_year"  # not stored, and without a year we cannot search Lawphil


@dataclass(frozen=True)
class SearchResult:
    status: SearchStatus
    cases: list[Case]


class SearchCaseByGrNumber:
    """Search by G.R. number. Stored cases return at once; unknown ones are fetched in
    the background so the HTTP request never waits on Lawphil."""

    def __init__(self, cases: CaseRepository, jobs: JobQueue, catalog: CatalogRepository | None = None) -> None:
        self._cases = cases
        self._jobs = jobs
        self._catalog = catalog

    def execute(self, gr_no: GrNumber, year: int | None) -> SearchResult:
        stored = self._cases.find_by_gr_no(gr_no)
        if stored:
            return SearchResult(SearchStatus.FOUND, stored)
        known_to_lawphil = self._catalog is not None and bool(self._catalog.find_by_number(gr_no))
        if year is None and not known_to_lawphil:
            return SearchResult(SearchStatus.NEEDS_YEAR, [])
        self._jobs.enqueue_fetch_case(str(gr_no), year)
        return SearchResult(SearchStatus.PENDING, [])
