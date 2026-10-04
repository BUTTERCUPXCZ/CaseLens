"""Read-only views derived from stored cases. Nothing here is generated or guessed:
every value is parsed from the official text or counted from stored rows."""
from dataclasses import dataclass, field
from datetime import date

from caselens.domain.entities import CitedCase, Statute
from caselens.domain.value_objects import Disposition, DocType


@dataclass(frozen=True)
class OpinionRef:
    kind: str
    author: str | None


@dataclass(frozen=True)
class CaseInsights:
    case_id: int
    gr_no: str
    title: str | None
    source_url: str
    decision_date: date | None
    doc_type: DocType
    division: str | None
    ponente: str | None
    disposition: Disposition
    ruling: str | None  # the dispositive paragraphs, verbatim from the decision
    concurring_justices: list[str]
    opinions: list[OpinionRef]
    statutes: list[Statute]
    cited_cases: list[CitedCase]
    footnote_count: int
    word_count: int


@dataclass(frozen=True)
class StatuteCount:
    statute_type: str
    number: str
    cases: int  # number of stored decisions that cite it


@dataclass(frozen=True)
class DispositionCount:
    year: int
    disposition: str
    cases: int


@dataclass(frozen=True)
class CitedCaseCount:
    title: str
    gr_no: str | None
    cases: int  # number of stored decisions that cite it


@dataclass(frozen=True)
class PonenteCount:
    ponente: str
    cases: int


@dataclass(frozen=True)
class TrendsReport:
    total_cases: int
    minimum_cases: int
    enough_data: bool  # False means "store more cases before reading patterns into this"
    top_statutes: list[StatuteCount] = field(default_factory=list)
    dispositions_by_year: list[DispositionCount] = field(default_factory=list)
    most_cited_cases: list[CitedCaseCount] = field(default_factory=list)
    cases_per_ponente: list[PonenteCount] = field(default_factory=list)
