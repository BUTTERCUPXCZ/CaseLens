import re
from dataclasses import dataclass, field
from datetime import date
from enum import Enum

_GR_PATTERN = re.compile(r"^(?:L-?\d{3,6}|\d{3,7})$")


@dataclass(frozen=True)
class GrNumber:
    """A Supreme Court docket number, e.g. `180046` or `L-12345`."""

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().upper()
        if not _GR_PATTERN.match(normalized):
            raise ValueError(f"Not a valid G.R. number: {self.value!r}")
        if normalized.startswith("L") and not normalized.startswith("L-"):
            normalized = "L-" + normalized[1:]
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class ClaimedCitation:
    """What a student's document *claims* about a case. Never trusted as fact."""

    gr_number: GrNumber
    raw: str
    title: str | None = None
    claimed_date: date | None = None
    claimed_year: int | None = None
    reporter: str | None = None  # e.g. "538 SCRA 428"; Lawphil text cannot verify it


class DocType(str, Enum):
    DECISION = "decision"
    RESOLUTION = "resolution"
    SEPARATE_OPINION = "separate_opinion"
    UNKNOWN = "unknown"


class Disposition(str, Enum):
    GRANTED = "GRANTED"
    DENIED = "DENIED"
    PARTIALLY_GRANTED = "PARTIALLY_GRANTED"
    DISMISSED = "DISMISSED"
    AFFIRMED = "AFFIRMED"
    REVERSED = "REVERSED"
    UNKNOWN = "UNKNOWN"


class StatuteType(str, Enum):
    REPUBLIC_ACT = "RA"
    EXECUTIVE_ORDER = "EO"
    BATAS_PAMBANSA = "BP"
    COMMONWEALTH_ACT = "CA"
    CONSTITUTION = "CONST"


class MatchStatus(str, Enum):
    PENDING = "pending"
    MATCH = "match"
    MISMATCH = "mismatch"
    NOT_FOUND = "not_found"
    ERROR = "error"  # could not be checked (source down, page unreadable); can be retried


@dataclass(frozen=True)
class MatchResult:
    status: MatchStatus
    mismatches: dict[str, dict] = field(default_factory=dict)
    unverified: list[str] = field(default_factory=list)
