import logging
from collections.abc import Callable
from dataclasses import dataclass, field

from caselens.application.ports.catalog import CatalogRepository
from caselens.application.use_cases.ingest_case import IngestCase
from caselens.domain.errors import DomainError, SourceUnavailableError

logger = logging.getLogger(__name__)

_BATCH = 200
_GIVE_UP_AFTER = 25  # this many failures in a row: Lawphil is down or has blocked us, so stop instead of hammering it


@dataclass
class DownloadReport:
    saved: int = 0
    failed: list[tuple[str, str]] = field(default_factory=list)  # (page address, reason)
    stopped: str | None = None  # why it stopped early


class DownloadCatalogCases:
    """Saves every decision of Lawphil's list that is not saved yet, so the app serves them from its own database.

    One page at a time through `IngestCase` (the polite 1-request-per-second fetcher, the parser, the family rule), each committed on its
    own, so it can be stopped any time and run again: it carries on with the pages that are still missing. Pages that failed are tried again next run.
    No AI is used and no digest is started."""

    def __init__(self, catalog: CatalogRepository, ingest: IngestCase, rollback: Callable[[], None]) -> None:
        self._catalog = catalog
        self._ingest = ingest
        self._rollback = rollback

    def execute(
        self,
        first_year: int,
        last_year: int,
        limit: int | None = None,
        on_progress: Callable[[DownloadReport, int], None] | None = None,
    ) -> DownloadReport:
        report, cursor, in_a_row = DownloadReport(), 0, 0
        while limit is None or report.saved + len(report.failed) < limit:
            batch = self._catalog.unsaved(first_year, last_year, cursor, _BATCH)
            if not batch:
                break
            for entry_id, url in batch:
                cursor = entry_id
                if limit is not None and report.saved + len(report.failed) >= limit:
                    break
                try:
                    self._ingest.execute(url)
                    report.saved += 1
                    in_a_row = 0
                except DomainError as exc:
                    self._rollback()
                    report.failed.append((url, str(exc)))
                    logger.warning("not saved %s: %s", url, exc)
                    in_a_row += 1 if isinstance(exc, SourceUnavailableError) else 0
                    if in_a_row >= _GIVE_UP_AFTER:
                        report.stopped = f"Lawphil did not answer {in_a_row} times in a row. Run it again later."
                        return report
                if on_progress:
                    on_progress(report, entry_id)
        return report
