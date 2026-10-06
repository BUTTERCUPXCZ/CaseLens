from collections.abc import Callable
from datetime import date

from caselens.application.ports.catalog import CatalogRepository
from caselens.application.ports.gateways import CaseFetcher, CaseLocator
from caselens.application.ports.repositories import MonthIndexRepository
from caselens.domain.errors import CaseNotFoundError, InvalidSourceUrlError
from caselens.domain.value_objects import GrNumber
from caselens.infrastructure.lawphil.http_client import ThrottledPageClient
from caselens.infrastructure.lawphil.url_scheme import CaseLink, LawphilUrlScheme

_EARLIEST_YEAR = 1900


class LawphilCaseSource(CaseLocator, CaseFetcher):
    """Locates and downloads cases from lawphil.net.

    First choice: the catalog, Lawphil's own monthly lists kept in our database. It knows the
    page for any G.R. number from 1987 on, whatever year the student wrote (or none), and
    answers without a single request to Lawphil.

    Fallback, when the catalog has nothing for the number (not built yet, or an older case):
    read the month-index pages around the year the student claims. The claimed year can be
    wrong (the sample reviewer says 2010; the case is 2009), hence the search radius. With no
    year and no catalog entry we do not guess: G.R. numbers do not map to years.
    """

    def __init__(
        self,
        pages: ThrottledPageClient,
        month_indexes: MonthIndexRepository,
        scheme: LawphilUrlScheme,
        search_radius: int = 2,
        today: Callable[[], date] = date.today,
        catalog: CatalogRepository | None = None,
    ) -> None:
        self._pages = pages
        self._month_indexes = month_indexes
        self._scheme = scheme
        self._radius = search_radius
        self._today = today
        self._catalog = catalog

    # -- CaseLocator --------------------------------------------------------------

    def locate(self, gr_no: GrNumber, claimed_year: int | None) -> list[str]:
        if self._catalog is not None:
            # Oldest first: a number's Decision comes before the Resolutions on it (a motion for reconsideration is decided later),
            # and the Decision is the case a student means. An undated row goes last.
            entries = sorted(self._catalog.find_by_number(gr_no), key=lambda e: (e.decision_date is None, e.decision_date or date.min))
            from_catalog = list(dict.fromkeys(e.source_url for e in entries))
            if from_catalog:
                return from_catalog
        if claimed_year is None:
            return []
        for year in self._candidate_years(claimed_year):
            links = self._links_for_year(gr_no, year)
            if links:
                links.sort(key=lambda link: link.suffix is not None)  # primary decision first
                return [link.url for link in links]
        return []

    def _candidate_years(self, claimed_year: int) -> list[int]:
        ordered = [claimed_year]
        for step in range(1, self._radius + 1):
            ordered += [claimed_year - step, claimed_year + step]
        return [y for y in ordered if _EARLIEST_YEAR <= y <= self._today().year]

    def _links_for_year(self, gr_no: GrNumber, year: int) -> list[CaseLink]:
        found: list[CaseLink] = []
        for month in range(1, 13):
            for url in self._case_urls(year, month):
                link = self._scheme.parse_case_link(url)
                if link and link.is_for(gr_no):
                    found.append(link)
        return found

    def _case_urls(self, year: int, month: int) -> list[str]:
        index_url = self._scheme.month_index_url(year, month)
        cached = self._month_indexes.get(index_url)
        if cached is not None:
            return cached

        html = self._pages.get_text(index_url)
        urls = self._scheme.case_urls_in_index(index_url, html) if html else []
        # A missing page in a finished year will never appear; in the current year it might.
        if html or year < self._today().year:
            self._month_indexes.save(index_url, urls)
        return urls

    # -- CaseFetcher --------------------------------------------------------------

    def fetch(self, url: str) -> str:
        if not self._scheme.is_official_case_url(url):
            raise InvalidSourceUrlError(f"Not an official Lawphil case URL: {url}")
        html = self._pages.get_text(url)
        if html is None:
            raise CaseNotFoundError(f"Lawphil has no page at {url}")
        return html
