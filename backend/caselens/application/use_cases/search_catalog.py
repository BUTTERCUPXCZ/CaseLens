from dataclasses import dataclass

from caselens.application.ports.catalog import CatalogRepository
from caselens.domain.entities import CatalogHit
from caselens.domain.services.catalog_query import CatalogQueryParser


@dataclass(frozen=True)
class CatalogPage:
    hits: list[CatalogHit]
    total: int
    limit: int
    offset: int
    understood_as: str  # "number" | "name" | "nothing": what we took the student's text to be


class SearchCatalog:
    """Search every decision on Lawphil's lists by case name or G.R. number.

    Answers from the local copy of the lists (a database query), so it never waits on Lawphil.
    Each hit says whether the case is already saved in the student's library."""

    def __init__(self, catalog: CatalogRepository, parser: CatalogQueryParser | None = None) -> None:
        self._catalog = catalog
        self._parser = parser or CatalogQueryParser()

    def execute(self, text: str, year: int | None, limit: int, offset: int) -> CatalogPage:
        query = self._parser.parse(text)
        if query.is_empty:
            return CatalogPage([], 0, limit, offset, "nothing")
        hits, total = self._catalog.search(query, year, limit, offset)
        return CatalogPage(hits, total, limit, offset, "number" if query.number else "name")
