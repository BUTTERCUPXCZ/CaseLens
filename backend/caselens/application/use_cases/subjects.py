from collections.abc import Sequence

from caselens.application.ports.repositories import CaseRepository, SubjectRepository, UnitOfWork
from caselens.domain.entities import CaseSummary
from caselens.domain.errors import CaseNotFoundError, DomainError
from caselens.domain.subjects import SOURCE_STUDENT, Subject, SubjectCount


class ListSubjects:
    """The library's filter: every subject with how many main cases are filed under it (and those with none yet)."""

    def __init__(self, cases: CaseRepository) -> None:
        self._cases = cases

    def execute(self) -> list[SubjectCount]:
        return self._cases.subject_counts()


class GetSubjects:
    """The subject list, for a picker."""

    def __init__(self, subjects: SubjectRepository) -> None:
        self._subjects = subjects

    def execute(self) -> list[Subject]:
        return self._subjects.list()


class SetCaseSubjects:
    """The student sets a case's tags (several, or none). The tags belong to the case, not to one page of it: they are set on the main case."""

    def __init__(self, cases: CaseRepository, subjects: SubjectRepository, uow: UnitOfWork) -> None:
        self._cases = cases
        self._subjects = subjects
        self._uow = uow

    def execute(self, case_id: int, subject_ids: Sequence[int]) -> CaseSummary:
        found = self._cases.summaries([case_id]).get(case_id)
        if found is None:
            raise CaseNotFoundError(f"Case {case_id} does not exist.")
        for subject_id in subject_ids:
            if self._subjects.get(subject_id) is None:
                raise DomainError(f"Subject {subject_id} does not exist.")
        main_id = found.main_case_id or case_id
        self._cases.set_subjects(main_id, list(dict.fromkeys(subject_ids)), SOURCE_STUDENT)
        self._uow.commit()
        return self._cases.summaries([main_id])[main_id]
