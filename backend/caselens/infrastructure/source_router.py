"""Two libraries of decisions behind the same ports: Lawphil first, the SC E-Library for what Lawphil does not have. A page is
read by the library its address belongs to."""
from caselens.application.ports.gateways import CaseFetcher, CaseLocator, CaseParser
from caselens.domain.entities import Case
from caselens.domain.errors import InvalidSourceUrlError
from caselens.domain.value_objects import GrNumber
from caselens.infrastructure.elibrary.url_scheme import ElibraryUrlScheme

SOURCE_NAMES = {"lawphil": "Lawphil", "elibrary": "SC E-Library"}


class LibraryRouter(CaseLocator, CaseFetcher, CaseParser):
    def __init__(
        self,
        lawphil: CaseLocator | CaseFetcher,
        lawphil_parser: CaseParser,
        elibrary: CaseLocator | CaseFetcher | None = None,
        elibrary_parser: CaseParser | None = None,
        elibrary_scheme: ElibraryUrlScheme | None = None,
    ) -> None:
        self._lawphil = lawphil
        self._lawphil_parser = lawphil_parser
        self._elibrary = elibrary
        self._elibrary_parser = elibrary_parser
        self._elibrary_scheme = elibrary_scheme

    def _is_elibrary(self, url: str) -> bool:
        return self._elibrary_scheme is not None and self._elibrary_scheme.is_official_case_url(url)

    def locate(self, gr_no: GrNumber, claimed_year: int | None) -> list[str]:
        """Lawphil's pages for the number; only when it has none, the E-Library's."""
        found = self._lawphil.locate(gr_no, claimed_year)
        if found or self._elibrary is None:
            return found
        return self._elibrary.locate(gr_no, claimed_year)

    def fetch(self, url: str) -> str:
        if self._is_elibrary(url):
            if self._elibrary is None:
                raise InvalidSourceUrlError("Reading the SC E-Library is turned off (ELIBRARY_ENABLED).")
            return self._elibrary.fetch(url)
        return self._lawphil.fetch(url)

    def parse(self, html: str, source_url: str) -> Case:
        if self._is_elibrary(source_url) and self._elibrary_parser is not None:
            return self._elibrary_parser.parse(html, source_url)
        return self._lawphil_parser.parse(html, source_url)


def source_of(url: str | None, elibrary_scheme: ElibraryUrlScheme) -> str:
    """"elibrary" for an E-Library decision address, otherwise "lawphil"."""
    return "elibrary" if url and elibrary_scheme.is_official_case_url(url) else "lawphil"

