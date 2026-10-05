from dataclasses import dataclass

from caselens.application.ports.bulk import BulkRepository
from caselens.application.ports.repositories import CaseRepository
from caselens.domain.entities import CaseSummary


@dataclass(frozen=True)
class CasePage:
    items: list[CaseSummary]
    total: int
    limit: int
    offset: int


class ListBatchCases:
    """What a bulk upload gave: its main cases, each once, in the order the student gave them. A case a later page made
    related is shown as its main case; nothing a file only cites is ever here."""

    def __init__(self, bulk: BulkRepository, cases: CaseRepository) -> None:
        self._bulk = bulk
        self._cases = cases

    def execute(self, batch_id: int, limit: int, offset: int) -> CasePage:
        ids = self._bulk.main_case_ids(batch_id)
        known = self._cases.summaries(ids)
        mains = list(dict.fromkeys((known[i].main_case_id or i) for i in ids if i in known))
        page_ids = mains[offset : offset + limit]
        shown = self._cases.summaries(page_ids)
        return CasePage([shown[i] for i in page_ids if i in shown], len(mains), limit, offset)


class ListCases:
    """The case library: one row per main case, optionally filtered by name or G.R. number and by subject."""

    def __init__(self, cases: CaseRepository) -> None:
        self._cases = cases

    def execute(self, query: str | None, limit: int, offset: int, subject_id: int | None = None, no_subject: bool = False) -> CasePage:
        cleaned = (query or "").strip() or None
        items, total = self._cases.search(cleaned, limit, offset, subject_id, no_subject)
        return CasePage(items, total, limit, offset)
