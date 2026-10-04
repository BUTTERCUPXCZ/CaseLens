from caselens.application.ports.gateways import JobQueue


class StartCatalogBuild:
    """Ask for the one-time read of Lawphil's monthly lists. A build already running wins."""

    def __init__(self, jobs: JobQueue, first_year: int) -> None:
        self._jobs = jobs
        self._first_year = first_year

    def execute(self) -> bool:
        return self._jobs.enqueue_build_catalog(self._first_year)
