import logging

from caselens.application.ports.gateways import CaseFetcher, CaseParser
from caselens.application.ports.repositories import CaseRepository, UnitOfWork
from caselens.domain.entities import Case
from caselens.domain.errors import DuplicateCaseError
from caselens.domain.services.case_family import CaseFamily, FamilyMember


logger = logging.getLogger(__name__)


class IngestCase:
    """Downloads one official page, parses it and stores it (once per URL).

    The page is also placed in its family: a Resolution, or the same decision under another G.R. number, is stored but linked to the main
    case already there, so the library shows one row per case (see `CaseFamily`)."""

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
        self._family = CaseFamily()

    def execute(self, url: str) -> Case:
        existing = self._cases.get_by_source_url(url)
        if existing:
            return existing

        case = self._parser.parse(self._fetcher.fetch(url), url)
        family = self._family.place(case.all_numbers, case.doc_type, self._members(case))
        case.main_case_id = family.main_case_id
        try:
            stored = self._cases.add(case)
        except DuplicateCaseError:  # another worker stored it between our check and insert
            existing = self._cases.get_by_source_url(url)
            assert existing is not None
            return existing
        if family.repoint:  # the new page outranks the main row that was there (a Decision over a Resolution): the family follows it
            self._cases.set_main_case(family.repoint, stored.id)
        self._uow.commit()
        logger.info("stored case G.R. No. %s from %s", stored.gr_no, url)
        return stored

    def _members(self, case: Case) -> list[FamilyMember]:
        return [
            FamilyMember(s.id, frozenset(s.numbers or (s.gr_no.value,)), s.doc_type, s.main_case_id)
            for s in self._cases.find_overlapping(case.all_numbers)
        ]
