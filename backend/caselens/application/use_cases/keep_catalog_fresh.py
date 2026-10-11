from caselens.application.ports.catalog import CatalogRepository
from caselens.application.ports.gateways import JobQueue


class KeepCatalogFresh:
    """Called on every catalog search. Costs nothing when there is nothing to do.

    * Nothing read yet, or a library none of whose lists has been read (the SC E-Library, after an update) -> start the
      one-time build (the queue ignores a second start; a library already read is skipped month by month).
    * Something read -> ask for the daily refresh of the newest months (the queue allows it
      once a day, so most calls do nothing).
    """

    def __init__(self, catalog: CatalogRepository, jobs: JobQueue, first_year: int, sources: list[str] | None = None) -> None:
        self._catalog = catalog
        self._jobs = jobs
        self._first_year = first_year
        self._sources = sources or ["lawphil"]

    def execute(self) -> str:
        status = self._catalog.status(building=False)
        if status.entries == 0 or any(not self._catalog.read_months(source) for source in self._sources):
            self._jobs.enqueue_build_catalog(self._first_year)
            return "building"
        self._jobs.enqueue_refresh_catalog()
        return status.state
