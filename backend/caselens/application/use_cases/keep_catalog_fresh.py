from caselens.application.ports.catalog import CatalogRepository
from caselens.application.ports.gateways import JobQueue


class KeepCatalogFresh:
    """Called on every catalog search. Costs nothing when there is nothing to do.

    * Nothing read yet -> start the one-time build (the queue ignores a second start).
    * Something read -> ask for the daily refresh of the newest months (the queue allows it
      once a day, so most calls do nothing).
    """

    def __init__(self, catalog: CatalogRepository, jobs: JobQueue, first_year: int) -> None:
        self._catalog = catalog
        self._jobs = jobs
        self._first_year = first_year

    def execute(self) -> str:
        status = self._catalog.status(building=False)
        if status.entries == 0:
            self._jobs.enqueue_build_catalog(self._first_year)
            return "building"
        self._jobs.enqueue_refresh_catalog()
        return status.state
