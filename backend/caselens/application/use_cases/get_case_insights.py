from caselens.application.ports.repositories import CaseRepository
from caselens.domain.errors import CaseNotFoundError
from caselens.domain.insights import CaseInsights
from caselens.domain.services.insight_builder import CaseInsightBuilder


class GetCaseInsights:
    def __init__(self, cases: CaseRepository, builder: CaseInsightBuilder) -> None:
        self._cases = cases
        self._builder = builder

    def execute(self, case_id: int) -> CaseInsights:
        case = self._cases.get(case_id)
        if case is None:
            raise CaseNotFoundError(f"Case {case_id} does not exist.")
        return self._builder.build(case)
