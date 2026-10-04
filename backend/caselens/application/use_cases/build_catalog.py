import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date

from caselens.application.ports.catalog import (
    CatalogIndexParser,
    CatalogRepository,
    IndexFetcher,
    YearDiscovery,
)
from caselens.domain.entities import IndexPage
from caselens.domain.errors import DomainError

logger = logging.getLogger(__name__)


@dataclass
class BuildReport:
    read: int = 0  # monthly lists read this run
    skipped: int = 0  # already read earlier (a build resumes where it stopped)
    entries: int = 0  # decisions stored by the lists read this run
    missing: list[str] = field(default_factory=list)  # listed by Lawphil but not downloadable
    failed: list[tuple[str, str]] = field(default_factory=list)  # (page url, reason)
    broken: list[str] = field(default_factory=list)  # had case links but nothing readable: layout changed?


class BuildCatalog:
    """Reads Lawphil's monthly lists into the searchable catalog.

    * Newest first, so recent cases can be searched within a minute of starting.
    * Safe to stop and start again: months already read are skipped.
    * The current and the previous month are always read again (new decisions are added to
      them), which is what `refresh` does on its own.
    * One bad month never stops the rest; it is reported at the end.
    """

    def __init__(
        self,
        discovery: YearDiscovery,
        fetcher: IndexFetcher,
        parser: CatalogIndexParser,
        catalog: CatalogRepository,
        today: Callable[[], date] = date.today,
    ) -> None:
        self._discovery = discovery
        self._fetcher = fetcher
        self._parser = parser
        self._catalog = catalog
        self._today = today

    def build(self, first_year: int) -> BuildReport:
        """Everything from `first_year` to now."""
        years = [y for y in self._discovery.years() if y >= first_year]
        pages = self._listed_months(sorted(years, reverse=True))
        self._catalog.register_months(pages)  # now progress has an honest total
        return self._read(sorted(pages, key=lambda p: (p.year, p.month), reverse=True))

    def refresh(self) -> BuildReport:
        """Only the current and the previous month (a few requests)."""
        recent = self._recent_months()
        years = sorted({year for year, _ in recent}, reverse=True)
        pages = [p for p in self._listed_months(years) if (p.year, p.month) in recent]
        self._catalog.register_months(pages)
        return self._read(sorted(pages, key=lambda p: (p.year, p.month), reverse=True))

    # -- steps --------------------------------------------------------------------

    def _listed_months(self, years: list[int]) -> list[IndexPage]:
        pages: list[IndexPage] = []
        for year in years:
            try:
                pages.extend(self._discovery.months(year))
            except DomainError as exc:  # a year page that will not load must not stop the others
                logger.warning("could not list the months of %s: %s", year, exc)
        return pages

    def _recent_months(self) -> set[tuple[int, int]]:
        today = self._today()
        previous = (today.year, today.month - 1) if today.month > 1 else (today.year - 1, 12)
        return {(today.year, today.month), previous}

    def _read(self, pages: list[IndexPage]) -> BuildReport:
        report = BuildReport()
        done = self._catalog.read_months()
        always = self._recent_months()

        for index, page in enumerate(pages, start=1):
            key = (page.year, page.month)
            if key in done and key not in always:
                report.skipped += 1
                continue
            try:
                html = self._fetcher.fetch(page.url)
            except DomainError as exc:
                logger.warning("could not read %s: %s", page.url, exc)
                report.failed.append((page.url, str(exc)))
                continue
            if html is None:
                report.missing.append(page.url)
                self._catalog.mark_absent(page)
                continue

            parsed = self._parser.parse(html, page.url)
            if parsed.looks_broken:
                logger.error("%s has case links but none could be read: has the layout changed?", page.url)
                report.broken.append(page.url)
                self._catalog.replace_month(page, [], broken=True)
                continue
            self._catalog.replace_month(page, parsed.entries)
            report.read += 1
            report.entries += len(parsed.entries)
            logger.info("read %s-%02d: %d decisions (%d of %d)", page.year, page.month, len(parsed.entries), index, len(pages))
        return report
