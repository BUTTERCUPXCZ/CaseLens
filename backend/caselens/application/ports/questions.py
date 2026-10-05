from abc import ABC, abstractmethod
from datetime import datetime

from caselens.domain.case_question import CaseQuestion


class CaseQuestionRepository(ABC):
    @abstractmethod
    def add(self, question: CaseQuestion) -> CaseQuestion:
        """Store a new question; returns it with its id and time."""

    @abstractmethod
    def get(self, question_id: int) -> CaseQuestion | None: ...

    @abstractmethod
    def save(self, question: CaseQuestion) -> None:
        """Store its state, answer and error."""

    @abstractmethod
    def list_for(self, case_id: int, batch_id: int | None) -> list[CaseQuestion]:
        """The questions asked about a case in one upload (or outside any upload when `batch_id` is None), oldest first."""

    @abstractmethod
    def count_since(self, since: datetime) -> int:
        """How many questions were asked since this moment (the daily cost guard)."""
