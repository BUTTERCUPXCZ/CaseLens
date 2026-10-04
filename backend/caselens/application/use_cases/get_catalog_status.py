from collections.abc import Callable

from caselens.application.ports.catalog import CatalogRepository
from caselens.domain.entities import CatalogStatus


class GetCatalogStatus:
    """How far the searchable copy of Lawphil's lists has got."""

    def __init__(self, catalog: CatalogRepository, build_is_running: Callable[[], bool]) -> None:
        self._catalog = catalog
        self._building = build_is_running

    def execute(self) -> CatalogStatus:
        return self._catalog.status(building=self._building())
