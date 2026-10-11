from caselens.application.ports.catalog import CatalogRepository
from caselens.application.ports.gateways import CaseFetcher, CaseLocator
from caselens.domain.errors import CaseNotFoundError, InvalidSourceUrlError
from caselens.domain.value_objects import GrNumber
from caselens.infrastructure.elibrary.url_scheme import ElibraryUrlScheme
from caselens.infrastructure.lawphil.http_client import ThrottledPageClient


class ElibraryCaseSource(CaseLocator, CaseFetcher):
    """Locates decisions through the E-Library rows of the catalog, and downloads them from the E-Library.

    There is no guessing by year here: the E-Library's addresses are document ids, not G.R. numbers, so a decision is found only
    through its monthly list (read into the catalog)."""

    def __init__(self, pages: ThrottledPageClient, scheme: ElibraryUrlScheme, catalog: CatalogRepository) -> None:
        self._pages = pages
        self._scheme = scheme
        self._catalog = catalog

    def locate(self, gr_no: GrNumber, claimed_year: int | None) -> list[str]:
        # Oldest first, as for Lawphil: a number's Decision comes before the Resolutions decided on it later.
        entries = [e for e in self._catalog.find_by_number(gr_no) if self._scheme.is_official_case_url(e.source_url)]
        entries.sort(key=lambda e: (e.decision_date is None, e.decision_date.toordinal() if e.decision_date else 0))
        return list(dict.fromkeys(e.source_url for e in entries))

    def fetch(self, url: str) -> str:
        if not self._scheme.is_official_case_url(url):
            raise InvalidSourceUrlError(f"Not an official SC E-Library decision URL: {url}")
        html = self._pages.get_text(self._scheme.canonical(url))
        if html is None:
            raise CaseNotFoundError(f"The SC E-Library has no page at {url}")
        return html
