from caselens.application.ports.gateways import CaseLocator
from caselens.application.ports.repositories import CaseRepository
from caselens.application.use_cases.ingest_case import IngestCase
from caselens.domain.entities import Case
from caselens.domain.errors import CaseNotFoundError
from caselens.domain.value_objects import DocType, GrNumber


class FetchCaseByGrNumber:
    """Returns the stored case for a G.R. number, downloading it first if needed."""

    def __init__(self, locator: CaseLocator, ingest: IngestCase, cases: CaseRepository) -> None:
        self._locator = locator
        self._ingest = ingest
        self._cases = cases

    def execute(self, gr_no: GrNumber, claimed_year: int | None) -> Case:
        stored = self.find_stored(gr_no)
        if stored:
            return stored

        # The locator knows the answer without a year when the catalog has the number, so it is
        # always asked; "no year" only matters when it comes back empty.
        urls = self._locator.locate(gr_no, claimed_year)
        if not urls:
            if claimed_year is None:
                raise CaseNotFoundError(
                    f"G.R. No. {gr_no} is not stored yet and no year was given to search "
                    "for it. Add the year, or paste the Lawphil URL."
                )
            raise CaseNotFoundError(f"G.R. No. {gr_no} was not found on Lawphil near {claimed_year}.")
        return self._ingest.execute(urls[0])  # primary decision is listed first

    def find_stored(self, gr_no: GrNumber) -> Case | None:
        """The stored primary document for this number, if we already have it."""
        cases = self._cases.find_by_gr_no(gr_no)
        decisions = [c for c in cases if c.doc_type is DocType.DECISION]
        return (decisions or cases or [None])[0]
