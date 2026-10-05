"""Ports for the searchable catalog of Lawphil's monthly lists."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from caselens.domain.entities import CatalogEntry, CatalogHit, CatalogStatus, IndexPage
from caselens.domain.services.catalog_query import CatalogQuery
from caselens.domain.value_objects import GrNumber


@dataclass(frozen=True)
class ParsedIndex:
    """What one monthly list contained."""

    entries: list[CatalogEntry]
    link_rows: int  # rows with a link of any kind (G.R., A.M., A.C., B.M.)
    other_kinds: dict[str, int] = field(default_factory=dict)  # e.g. {"am": 11}: not G.R. cases, skipped
    unreadable: int = 0  # G.R. rows whose number or link could not be read

    @property
    def looks_broken(self) -> bool:
        """The page has case links, yet nothing could be read: the layout probably changed."""
        return self.link_rows > 0 and not self.entries and not self.other_kinds


class CatalogIndexParser(ABC):
    """Reads one monthly list page."""

    @abstractmethod
    def parse(self, html: str, index_url: str) -> ParsedIndex: ...


class IndexFetcher(ABC):
    """Downloads one of Lawphil's list pages. A page that does not exist is None, not an error."""

    @abstractmethod
    def fetch(self, url: str) -> str | None: ...


class YearDiscovery(ABC):
    """Finds which monthly lists Lawphil actually has (months can be missing)."""

    @abstractmethod
    def years(self) -> list[int]:
        """Years Lawphil lists, oldest first (future years excluded)."""

    @abstractmethod
    def months(self, year: int) -> list[IndexPage]:
        """The monthly lists that exist for this year, January first."""


class CatalogRepository(ABC):
    @abstractmethod
    def replace_month(self, page: IndexPage, entries: list[CatalogEntry], broken: bool = False) -> None:
        """Store what one monthly list contained (replacing an earlier read of the same page)
        and remember that this month has been read. `broken` records a page that had case
        links but nothing readable, so it is reported instead of silently counted as empty."""

    @abstractmethod
    def mark_absent(self, page: IndexPage) -> None:
        """Lawphil lists this month but its page does not exist. Counted as handled for progress,
        yet not as read, so a later build looks again (one cheap request)."""

    @abstractmethod
    def register_months(self, pages: list[IndexPage]) -> None:
        """Remember that these monthly lists exist (as `pending` unless already read), so
        progress can be shown against a known total."""

    @abstractmethod
    def read_months(self) -> set[tuple[int, int]]:
        """(year, month) of every list already read."""

    @abstractmethod
    def search(
        self, query: CatalogQuery, year: int | None, limit: int, offset: int
    ) -> tuple[list[CatalogHit], int]:
        """Matches newest first, with the total, and the saved case id where there is one.
        `year` narrows to decisions of that year."""

    @abstractmethod
    def find_by_number(self, gr_no: GrNumber) -> list[CatalogEntry]:
        """Where this G.R. number can be opened (including as part of a joint decision)."""

    @abstractmethod
    def unsaved(self, first_year: int, last_year: int, after_id: int, limit: int) -> list[tuple[int, str]]:
        """(cursor, page address) of the catalog decisions not saved as cases yet, each page once, oldest list row first,
        only those after the cursor. A joint decision listed under several numbers is one page."""

    @abstractmethod
    def status(self, building: bool) -> CatalogStatus: ...
