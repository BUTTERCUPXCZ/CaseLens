"""Core business objects. Plain dataclasses: no framework, no database, no HTTP."""
from dataclasses import dataclass, field
from datetime import date, datetime

from caselens.domain.subjects import Subject
from caselens.domain.value_objects import (
    ClaimedCitation,
    DocType,
    Disposition,
    GrNumber,
    MatchResult,
    MatchStatus,
    StatuteType,
)


@dataclass
class Footnote:
    number: int
    anchor: str  # Lawphil anchor name, e.g. "fnt19" (opinions: "fnt3b")
    text: str


@dataclass
class Opinion:
    """Separate/concurring/dissenting opinion printed on the same page as a decision."""

    kind: str
    author: str | None
    text: str
    footnotes: list[Footnote] = field(default_factory=list)


@dataclass(frozen=True)
class Statute:
    statute_type: StatuteType
    number: str  # "7722", or "Art. VI, Sec. 1" for the Constitution
    raw: str


@dataclass(frozen=True)
class CitedCase:
    title: str
    gr_no: str | None
    source: str  # "body" | "footnote"
    footnote_number: int | None = None  # which footnote cites it (links to #fntN on Lawphil)


@dataclass
class Case:
    """One official document. `full_text` keeps footnote markers as `[^N]`."""

    gr_no: GrNumber
    source_url: str
    title: str | None
    decision_date: date | None
    doc_type: DocType
    ponente: str | None
    division: str | None
    disposition: Disposition
    raw_html: str
    full_text: str
    parser_version: int
    footnotes: list[Footnote] = field(default_factory=list)
    opinions: list[Opinion] = field(default_factory=list)
    statutes: list[Statute] = field(default_factory=list)
    cited_cases: list[CitedCase] = field(default_factory=list)
    id: int | None = None
    fetched_at: datetime | None = None
    # Every G.R. number the page itself prints. A joint decision has several; `gr_no` is the first.
    numbers: tuple[str, ...] = ()
    subjects: tuple["Subject", ...] = ()  # the tags the student gave it (Constitutional Law, ...), in the list's order; read from the database
    main_case_id: int | None = None  # None: this is a main case; otherwise the main case this page belongs to

    @property
    def all_numbers(self) -> tuple[str, ...]:
        """The numbers this decision settles; just `gr_no` for rows stored before this was read."""
        return self.numbers or (self.gr_no.value,)

    def footnote_url(self, number: int) -> str:
        """Deep link to a footnote on the official page."""
        return f"{self.source_url}#fnt{number}"


@dataclass
class UploadedCitation:
    """A citation found in an upload, together with the outcome of checking it."""

    claimed: ClaimedCitation
    status: MatchStatus = MatchStatus.PENDING
    matched_case_id: int | None = None
    mismatches: dict[str, dict] = field(default_factory=dict)
    unverified: list[str] = field(default_factory=list)  # claims the official text cannot confirm
    message: str | None = None  # why it is not_found / error
    id: int | None = None

    def record_match(self, result: MatchResult, case_id: int | None) -> None:
        self.status = result.status
        self.matched_case_id = case_id
        self.mismatches = result.mismatches
        self.unverified = result.unverified
        self.message = None

    def record_failure(self, status: MatchStatus, message: str) -> None:
        self.status = status
        self.message = message

    def reset_for_retry(self) -> None:
        """Back to pending so the background worker checks it again."""
        self.status = MatchStatus.PENDING
        self.message = None
        self.matched_case_id = None
        self.mismatches = {}
        self.unverified = []


@dataclass(frozen=True)
class CaseSummary:
    """A case without its (large) text: enough for a list or a search result."""

    id: int
    gr_no: GrNumber
    title: str | None
    decision_date: date | None
    doc_type: DocType
    ponente: str | None
    division: str | None
    disposition: Disposition
    source_url: str
    subjects: tuple["Subject", ...] = ()  # its tags, in the list's order
    main_case_id: int | None = None
    numbers: tuple[str, ...] = ()  # every G.R. number the page prints


@dataclass(frozen=True)
class CatalogEntry:
    """One row of Lawphil's monthly list of decisions.

    `numbers` are the G.R. numbers *printed* on the row (a joint decision lists several);
    `gr_no` is the number in the row's *link*, i.e. the page we can open. They normally agree.
    Lawphil's own list has rows whose label and link differ (a typo, or a sibling petition),
    so searches go by the label and opening goes by the link."""

    gr_no: GrNumber
    numbers: tuple[str, ...]
    title: str  # the parties, e.g. "Gilbert Dela Paz vs. People of the Philippines"
    decision_date: date | None
    source_url: str
    index_url: str

    @property
    def also_decided_with(self) -> tuple[str, ...]:
        """Other numbers printed on the same row (a joint decision), without this page's own."""
        return tuple(n for n in self.numbers if n != self.gr_no.value)


@dataclass(frozen=True)
class IndexPage:
    """One of Lawphil's monthly list pages."""

    year: int
    month: int
    url: str


@dataclass(frozen=True)
class CatalogHit:
    entry: CatalogEntry
    case_id: int | None  # set when this case is already saved in the library


@dataclass(frozen=True)
class CatalogStatus:
    entries: int
    months_read: int
    months_known: int  # months Lawphil lists for the years we cover (0 until the year pages are read)
    state: str  # "empty" | "building" | "partial" (stopped before the end) | "ready"

    @property
    def percent(self) -> int:
        return 100 if self.months_known and self.months_read >= self.months_known else (
            int(100 * self.months_read / self.months_known) if self.months_known else 0
        )


@dataclass(frozen=True)
class UploadSummary:
    """An upload without its text, with how its citations came out."""

    id: int
    filename: str
    status: str
    created_at: datetime | None
    matched: int = 0
    needs_look: int = 0  # claimed details differ from the official record
    not_found: int = 0
    errors: int = 0
    pending: int = 0

    @property
    def total(self) -> int:
        return self.matched + self.needs_look + self.not_found + self.errors + self.pending


@dataclass
class Upload:
    filename: str
    text: str
    citations: list[UploadedCitation] = field(default_factory=list)
    status: str = "pending"
    id: int | None = None
    created_at: datetime | None = None
    file_data: bytes | None = None  # the original file, kept so the finished reviewer can be built from it
