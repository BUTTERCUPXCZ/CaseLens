from dataclasses import dataclass

from caselens.application.ports.repositories import CaseRepository
from caselens.domain.entities import CaseSummary


@dataclass(frozen=True)
class CasePage:
    items: list[CaseSummary]
    total: int
    limit: int
    offset: int


class ListCases:
    """The case library: every stored case, optionally filtered by name or G.R. number."""

    def __init__(self, cases: CaseRepository) -> None:
        self._cases = cases

    def execute(self, query: str | None, limit: int, offset: int) -> CasePage:
        cleaned = (query or "").strip() or None
        items, total = self._cases.search(cleaned, limit, offset)
        return CasePage(items, total, limit, offset)
