"""One case, one row: decide whether a newly stored page is the MAIN case or only related to one that is already stored.

A decision and its later Resolution, one decision printed under several G.R. numbers (joint or consolidated), and the same page found
twice all describe ONE case. The library lists only the main row; the rest are kept (their text is the Court's) but linked to it."""
from collections.abc import Sequence
from dataclasses import dataclass

from caselens.domain.value_objects import DocType

_RANK = {DocType.DECISION: 3, DocType.UNKNOWN: 2, DocType.RESOLUTION: 1, DocType.SEPARATE_OPINION: 0}


@dataclass(frozen=True)
class FamilyMember:
    """What the decision needs to know about a stored page (the numbers it settles, what kind of document it is, and its main row)."""

    id: int
    numbers: frozenset[str]
    doc_type: DocType
    main_case_id: int | None  # None: this row is itself a main case


@dataclass(frozen=True)
class FamilyDecision:
    main_case_id: int | None  # the new page's main case; None = the new page IS the main case
    repoint: tuple[int, ...] = ()  # stored rows that must now point at the new page (it outranks their old main)


class CaseFamily:
    def place(self, numbers: Sequence[str], doc_type: DocType, stored: Sequence[FamilyMember]) -> FamilyDecision:
        """`stored` are the pages that print any of `numbers`. If none, the new page is a main case. Otherwise it joins the family of their
        main row, unless it outranks it (a Decision over a Resolution), in which case it becomes the main row and the family follows it."""
        mine = set(numbers)
        related = [m for m in stored if m.numbers & mine]
        if not related:
            return FamilyDecision(None)
        mains = {m.main_case_id or m.id for m in related}
        by_id = {m.id: m for m in stored}
        main = max((by_id[i] for i in mains if i in by_id), key=lambda m: (_RANK[m.doc_type], -m.id), default=None)
        if main is None:
            return FamilyDecision(None)
        if _RANK[doc_type] > _RANK[main.doc_type]:
            members = [m.id for m in related if (m.main_case_id or m.id) in mains]
            return FamilyDecision(None, tuple(dict.fromkeys([main.id, *members])))
        return FamilyDecision(main.id)
