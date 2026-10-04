import logging
from dataclasses import dataclass, field

from caselens.application.ports.gateways import CaseParser
from caselens.application.ports.repositories import CaseRepository, UnitOfWork
from caselens.domain.errors import CaseParseError

logger = logging.getLogger(__name__)


@dataclass
class ReparseReport:
    updated: int = 0
    failed: list[tuple[int, str, str]] = field(default_factory=list)  # (case id, url, reason)


class ReparseStoredCases:
    """Re-reads the stored `raw_html` of cases parsed by an older parser version.

    No network access: this is why the original page is kept. When the parser improves,
    existing cases are fixed in place instead of being downloaded from Lawphil again.
    """

    def __init__(
        self,
        cases: CaseRepository,
        parser: CaseParser,
        current_parser_version: int,
        uow: UnitOfWork,
    ) -> None:
        self._cases = cases
        self._parser = parser
        self._version = current_parser_version
        self._uow = uow

    def execute(self) -> ReparseReport:
        report = ReparseReport()
        for case_id, url, raw_html in self._cases.outdated(self._version):
            try:
                parsed = self._parser.parse(raw_html, url)
            except CaseParseError as exc:
                logger.warning("reparse case %s (%s) failed: %s", case_id, url, exc)
                report.failed.append((case_id, url, str(exc)))
                continue
            self._cases.update_content(case_id, parsed)
            self._uow.commit()
            report.updated += 1
        return report
