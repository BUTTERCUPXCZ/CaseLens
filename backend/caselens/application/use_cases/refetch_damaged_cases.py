import logging
from dataclasses import dataclass, field

from caselens.application.ports.gateways import CaseFetcher, CaseParser
from caselens.application.ports.repositories import CaseRepository, UnitOfWork
from caselens.domain.errors import DomainError

logger = logging.getLogger(__name__)


@dataclass
class RefetchReport:
    repaired: int = 0
    failed: list[tuple[int, str, str]] = field(default_factory=list)  # (case id, url, reason)


class RefetchDamagedCases:
    """Download again the cases whose stored text was damaged on the way in.

    Re-parsing cannot help here: the damage (a replacement character where an apostrophe or
    quote should be) is already in the stored page, so the page has to be fetched once more.
    Needs the network and is throttled like any other fetch.
    """

    def __init__(
        self,
        cases: CaseRepository,
        fetcher: CaseFetcher,
        parser: CaseParser,
        uow: UnitOfWork,
    ) -> None:
        self._cases = cases
        self._fetcher = fetcher
        self._parser = parser
        self._uow = uow

    def execute(self) -> RefetchReport:
        report = RefetchReport()
        for case_id, url in self._cases.with_damaged_text():
            try:
                parsed = self._parser.parse(self._fetcher.fetch(url), url)
            except DomainError as exc:
                logger.warning("could not refetch case %s (%s): %s", case_id, url, exc)
                report.failed.append((case_id, url, str(exc)))
                continue
            self._cases.update_content(case_id, parsed)
            self._uow.commit()
            report.repaired += 1
        return report
