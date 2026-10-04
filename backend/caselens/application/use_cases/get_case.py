from caselens.application.ports.repositories import CaseRepository
from caselens.domain.entities import Case
from caselens.domain.errors import CaseNotFoundError


class GetCase:
    def __init__(self, cases: CaseRepository) -> None:
        self._cases = cases

    def execute(self, case_id: int) -> Case:
        case = self._cases.get(case_id)
        if case is None:
            raise CaseNotFoundError(f"Case {case_id} does not exist.")
        return case
