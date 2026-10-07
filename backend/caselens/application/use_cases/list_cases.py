import re
from dataclasses import dataclass, field

from caselens.application.ports.bulk import BulkRepository
from caselens.application.ports.digests import CaseDigestRepository
from caselens.application.ports.repositories import CaseRepository
from caselens.domain.digest_v2 import scope_key
from caselens.domain.entities import CaseSummary


@dataclass(frozen=True)
class CasePage:
    items: list[CaseSummary]
    total: int
    limit: int
    offset: int


# What the student can filter an upload's cases by, while its digests are still being written.
BATCH_STATE_FILTERS = {"ready": {"ready"}, "writing": {"pending", "none"}, "failed": {"failed"}}


@dataclass(frozen=True)
class BatchCasePage(CasePage):
    states: dict[int, str] = field(default_factory=dict)  # each case's digest for this upload's topic scope
    counts: dict[str, int] = field(default_factory=dict)  # how many cases are ready / being written / failed, over the whole upload


class ListBatchCases:
    """What a bulk upload gave: its main cases, each once, in the order the student gave them. A case a later page made
    related is shown as its main case; nothing a file only cites is ever here. While digests are written, the list can be
    narrowed to the ready ones (or the ones still being written), so the student studies those first."""

    def __init__(self, bulk: BulkRepository, cases: CaseRepository, digests: CaseDigestRepository | None = None) -> None:
        self._bulk = bulk
        self._cases = cases
        self._digests = digests

    def execute(self, batch_id: int, limit: int, offset: int, state: str | None = None, query: str | None = None) -> BatchCasePage:
        """`query`: words of the case name, or the start of a G.R. number ("Ralla", "63253", "G.R. No. L-6325"). The counts stay those
        of the whole upload; only the list is narrowed."""
        ids = self._bulk.main_case_ids(batch_id)
        known = self._cases.summaries(ids)
        mains = list(dict.fromkeys((known[i].main_case_id or i) for i in ids if i in known))
        states: dict[int, str] = {}
        if self._digests is not None:
            batch = self._bulk.get_batch(batch_id)
            found = self._digests.states(mains, scope_key(batch.topic_scope if batch else ""))
            states = {i: found.get(i, "none") for i in mains}
        counts = {name: sum(1 for i in mains if states.get(i, "none") in wanted) for name, wanted in BATCH_STATE_FILTERS.items()}
        if state in BATCH_STATE_FILTERS:
            mains = [i for i in mains if states.get(i, "none") in BATCH_STATE_FILTERS[state]]
        if query and query.strip():
            named = self._cases.summaries(mains)
            mains = [i for i in mains if i in named and _matches(named[i], query)]
        page_ids = mains[offset : offset + limit]
        shown = self._cases.summaries(page_ids)
        return BatchCasePage([shown[i] for i in page_ids if i in shown], len(mains), limit, offset, {i: states[i] for i in page_ids if i in states}, counts)


_GR_LABEL = re.compile(r"^\s*g\.?\s?r\.?\s*(?:nos?\.?)?\s*", re.IGNORECASE)


def _matches(case: CaseSummary, query: str) -> bool:
    """A typed G.R. number matches the start of any number the case prints (with or without "L-"); words must all be in its name."""
    text = _GR_LABEL.sub("", query.strip()).strip().upper()
    numbers = case.numbers or (case.gr_no.value,)
    if re.fullmatch(r"L?-?\d+", text):
        digits = text.lstrip("L-")
        return any(n.upper().startswith(text) or n.upper().lstrip("L-").startswith(digits) for n in numbers)
    title = (case.title or "").lower()
    return all(word in title for word in query.lower().split())


class ListCases:
    """The case library: one row per main case, optionally filtered by name or G.R. number and by subject."""

    def __init__(self, cases: CaseRepository) -> None:
        self._cases = cases

    def execute(self, query: str | None, limit: int, offset: int, subject_id: int | None = None, no_subject: bool = False) -> CasePage:
        cleaned = (query or "").strip() or None
        items, total = self._cases.search(cleaned, limit, offset, subject_id, no_subject)
        return CasePage(items, total, limit, offset)
