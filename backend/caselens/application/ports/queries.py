"""Read-side port: aggregate questions over all stored cases (CQRS-style read model).

Kept apart from CaseRepository because these return counts, not entities."""
from abc import ABC, abstractmethod

from caselens.domain.insights import (
    CitedCaseCount,
    DispositionCount,
    PonenteCount,
    StatuteCount,
)


class InsightQueries(ABC):
    """Every method counts stored *decisions* only (not resolutions or opinions)."""

    @abstractmethod
    def total_cases(self) -> int: ...

    @abstractmethod
    def top_statutes(self, limit: int) -> list[StatuteCount]: ...

    @abstractmethod
    def dispositions_by_year(self) -> list[DispositionCount]: ...

    @abstractmethod
    def most_cited_cases(self, limit: int) -> list[CitedCaseCount]: ...

    @abstractmethod
    def cases_per_ponente(self, limit: int) -> list[PonenteCount]: ...
