import logging

from caselens.application.ports.gateways import CaseFetcher, CaseParser
from caselens.application.ports.repositories import CaseRepository, UnitOfWork
from caselens.domain.entities import Case
from caselens.domain.errors import DuplicateCaseError


logger = logging.getLogger(__name__)


class IngestCase:
    """Downloads one official page, parses it and stores it (once per URL)."""

    def __init__(
        self,
        fetcher: CaseFetcher,
        parser: CaseParser,
        cases: CaseRepository,
        uow: UnitOfWork,
    ) -> None:
        self._fetcher = fetcher
        self._parser = parser
        self._cases = cases
        self._uow = uow

    def execute(self, url: str) -> Case:
        existing = self._cases.get_by_source_url(url)
        if existing:
            return existing

        case = self._parser.parse(self._fetcher.fetch(url), url)
        try:
            stored = self._cases.add(case)
        except DuplicateCaseError:  # another worker stored it between our check and insert
            existing = self._cases.get_by_source_url(url)
            assert existing is not None
            return existing
        self._uow.commit()
        logger.info("stored case G.R. No. %s from %s", stored.gr_no, url)
        return stored
