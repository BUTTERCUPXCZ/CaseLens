from caselens.application.ports.gateways import CaseLocator
from caselens.application.ports.repositories import CaseRepository
from caselens.application.use_cases.ingest_case import IngestCase
from caselens.domain.entities import Case
from caselens.domain.errors import CaseNotFoundError, DomainError
from caselens.domain.value_objects import DocType, GrNumber


_PAGES_TO_TRY = 3  # at one page a second; a number rarely has more than a Decision and a Resolution or two


class FetchCaseByGrNumber:
    """Returns the stored case for a G.R. number, downloading it first if needed."""

    def __init__(self, locator: CaseLocator, ingest: IngestCase, cases: CaseRepository) -> None:
        self._locator = locator
        self._ingest = ingest
        self._cases = cases

    def execute(self, gr_no: GrNumber, claimed_year: int | None) -> Case:
        stored = self.find_stored(gr_no)
        if stored and stored.doc_type is DocType.DECISION:
            return stored
        # Only a Resolution (or an unknown page) is stored: the Decision may still be on Lawphil's list. Looking costs nothing for pages
        # already stored; if nothing better is found, the stored page is the answer.

        # The locator knows the answer without a year when the catalog has the number, so it is
        # always asked; "no year" only matters when it comes back empty.
        urls = self._locator.locate(gr_no, claimed_year)
        if not urls and stored:
            return stored
        if stored:
            try:
                return self._decision_among(urls)
            except DomainError:
                return stored  # Lawphil down: the page already in the library still answers
        if not urls:
            if claimed_year is None:
                raise CaseNotFoundError(
                    f"G.R. No. {gr_no} is not stored yet and no year was given to search "
                    "for it. Add the year, or paste the Lawphil URL."
                )
            raise CaseNotFoundError(f"G.R. No. {gr_no} was not found on Lawphil near {claimed_year}.")
        return self._decision_among(urls)

    def _decision_among(self, urls: list[str]) -> Case:
        """A number can have a Decision and later Resolutions, all on Lawphil's list under the same number (and often the same year). The
        list cannot tell them apart, the page can: open them in order (oldest first, so usually one page) until one is a Decision. If
        none of the first few is, the first page is the answer. Every page opened is stored, linked to its case (see `CaseFamily`)."""
        first: Case | None = None
        for url in urls[:_PAGES_TO_TRY]:
            try:
                case = self._ingest.execute(url)
            except DomainError:
                if first is None:
                    raise  # the first page failing is the answer (not found, Lawphil down): say so
                break  # a later page failing does not lose the one already found
            if case.doc_type is DocType.DECISION:
                return case
            first = first or case
        assert first is not None
        return first

    def find_stored(self, gr_no: GrNumber) -> Case | None:
        """The stored primary document for this number, if we already have it."""
        cases = self._cases.find_by_gr_no(gr_no)
        decisions = [c for c in cases if c.doc_type is DocType.DECISION]
        return (decisions or cases or [None])[0]
