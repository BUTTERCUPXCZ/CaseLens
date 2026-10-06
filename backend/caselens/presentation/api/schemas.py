"""HTTP request/response shapes. Entities are converted here, so the API contract can
change without touching the domain."""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from caselens.application.use_cases.get_upload import UploadReport
from caselens.application.use_cases.list_cases import CasePage
from caselens.application.use_cases.search_catalog import CatalogPage
from caselens.domain.entities import (
    Case,
    CaseSummary,
    CatalogHit,
    CatalogStatus,
    CitedCase,
    Footnote,
    UploadedCitation,
    UploadSummary,
)
from caselens.domain.insights import CaseInsights, TrendsReport


MatchStatusName = Literal["pending", "match", "mismatch", "not_found", "error"]
UploadStatusName = Literal["pending", "processing", "done"]
SearchStatusName = Literal["found", "pending", "needs_year"]
DocTypeName = Literal["decision", "resolution", "separate_opinion", "unknown"]
CatalogStateName = Literal["empty", "building", "partial", "ready"]
CatalogUnderstoodAs = Literal["number", "name", "nothing"]
DispositionName = Literal[
    "GRANTED", "DENIED", "PARTIALLY_GRANTED", "DISMISSED", "AFFIRMED", "REVERSED", "UNKNOWN"
]


class Attribution(BaseModel):
    """Shown with every response that presents official text. Wording follows Lawphil's own
    Acceptable Use Policy and Disclaimer (read 2026-10-03): informational only, no warranty
    of accuracy or completeness, confirm with the originating body."""

    source: str = "Lawphil (Arellano Law Foundation), https://lawphil.net"
    notice: str = (
        "Informational only, not legal advice. Lawphil gives no warranty of accuracy or "
        "completeness: confirm with the originating body (the Supreme Court)."
    )


class FootnoteOut(BaseModel):
    number: int
    anchor: str
    text: str
    source_url: str | None = None  # deep link to this footnote on the official page


class OpinionOut(BaseModel):
    kind: str
    author: str | None
    text: str
    footnotes: list[FootnoteOut]


class StatuteOut(BaseModel):
    type: str
    number: str
    raw: str


class CitedCaseOut(BaseModel):
    title: str
    gr_no: str | None
    source: str
    footnote_number: int | None = None
    source_url: str | None = None  # deep link to the citing footnote on the official page

    @classmethod
    def from_entity(cls, cited: CitedCase, case_url: str) -> "CitedCaseOut":
        return cls(
            title=cited.title,
            gr_no=cited.gr_no,
            source=cited.source,
            footnote_number=cited.footnote_number,
            source_url=f"{case_url}#fnt{cited.footnote_number}" if cited.footnote_number else case_url,
        )


class SubjectOut(BaseModel):
    id: int
    name: str


class CaseSummaryOut(BaseModel):
    id: int
    gr_no: str
    title: str | None
    decision_date: date | None
    doc_type: DocTypeName
    ponente: str | None
    division: str | None
    disposition: DispositionName
    source_url: str
    numbers: list[str] = []  # every G.R. number the page prints (a joint decision has several)
    subjects: list[SubjectOut] = []  # the tags the student gave it, in the list's order
    digest_ready: bool = False  # a case digest has been written for it
    digest_state: Literal["none", "pending", "ready", "failed"] = "none"  # and how it is coming along

    @classmethod
    def from_entity(cls, case: Case | CaseSummary, digest_ready: bool = False, digest_state: str = "none") -> "CaseSummaryOut":
        """Works for a full `Case` and for the lighter `CaseSummary` (same fields)."""
        return cls(
            id=case.id,
            gr_no=str(case.gr_no),
            title=case.title,
            decision_date=case.decision_date,
            doc_type=case.doc_type.value,
            ponente=case.ponente,
            division=case.division,
            disposition=case.disposition.value,
            source_url=case.source_url,
            numbers=list(case.all_numbers if isinstance(case, Case) else (case.numbers or (case.gr_no.value,))),
            subjects=[SubjectOut(id=s.id, name=s.name) for s in case.subjects],
            digest_ready=digest_ready,
            digest_state=digest_state,  # type: ignore[arg-type]
        )


class SubjectCountOut(BaseModel):
    subject_id: int | None  # None: cases with no subject yet
    name: str
    count: int


class SubjectsIn(BaseModel):
    subject_ids: list[int] = Field(default_factory=list, max_length=20)  # an empty list clears the tags


class CaseDetailOut(CaseSummaryOut):
    full_text: str
    fetched_at: datetime | None
    attribution: Attribution = Attribution()
    footnotes: list[FootnoteOut]
    opinions: list[OpinionOut]
    statutes: list[StatuteOut]
    cited_cases: list[CitedCaseOut]

    @classmethod
    def from_entity(cls, case: Case) -> "CaseDetailOut":
        def footnote(f: Footnote, link: bool) -> FootnoteOut:
            return FootnoteOut(
                number=f.number,
                anchor=f.anchor,
                text=f.text,
                source_url=f"{case.source_url}#{f.anchor}" if link else None,
            )

        return cls(
            **CaseSummaryOut.from_entity(case).model_dump(),
            full_text=case.full_text,
            fetched_at=case.fetched_at,
            footnotes=[footnote(f, True) for f in case.footnotes],
            opinions=[
                OpinionOut(
                    kind=o.kind,
                    author=o.author,
                    text=o.text,
                    footnotes=[footnote(f, True) for f in o.footnotes],
                )
                for o in case.opinions
            ],
            statutes=[
                StatuteOut(type=s.statute_type.value, number=s.number, raw=s.raw)
                for s in case.statutes
            ],
            cited_cases=[CitedCaseOut.from_entity(c, case.source_url) for c in case.cited_cases],
        )


class SearchOut(BaseModel):
    status: SearchStatusName
    cases: list[CaseSummaryOut]


class FetchByUrlIn(BaseModel):
    url: str


class CasePageOut(BaseModel):
    items: list[CaseSummaryOut]
    total: int
    limit: int
    offset: int
    # One upload's list only: how many of its cases are ready / being written / failed (for the filter above the list).
    state_counts: dict[str, int] | None = None

    @classmethod
    def from_page(cls, page: CasePage, digest_states: dict[int, str] | None = None) -> "CasePageOut":
        states = digest_states or {}
        return cls(
            items=[CaseSummaryOut.from_entity(c, digest_ready=states.get(c.id) == "ready", digest_state=states.get(c.id, "none")) for c in page.items],
            total=page.total,
            limit=page.limit,
            offset=page.offset,
        )


class UploadSummaryOut(BaseModel):
    id: int
    filename: str
    status: UploadStatusName
    created_at: datetime | None
    total: int
    matched: int
    needs_look: int
    not_found: int
    errors: int
    pending: int

    @classmethod
    def from_entity(cls, s: UploadSummary) -> "UploadSummaryOut":
        return cls(
            id=s.id,
            filename=s.filename,
            status=s.status,
            created_at=s.created_at,
            total=s.total,
            matched=s.matched,
            needs_look=s.needs_look,
            not_found=s.not_found,
            errors=s.errors,
            pending=s.pending,
        )


class ClaimedOut(BaseModel):
    title: str | None
    year: int | None
    date: date | None
    reporter: str | None


class MismatchOut(BaseModel):
    """One field where the student's citation differs from the official record."""

    claimed: str | int | None
    official: str | int | None


class CitationOut(BaseModel):
    id: int
    gr_no: str
    raw_citation: str
    claimed: ClaimedOut
    status: MatchStatusName
    mismatches: dict[str, MismatchOut]
    unverified: list[str]
    message: str | None
    case_id: int | None
    source_url: str | None
    case: CaseSummaryOut | None  # the official record this was checked against

    @classmethod
    def from_entity(cls, citation: UploadedCitation, cases: dict[int, CaseSummary]) -> "CitationOut":
        claimed = citation.claimed
        official = cases.get(citation.matched_case_id)
        return cls(
            id=citation.id,
            gr_no=str(claimed.gr_number),
            raw_citation=claimed.raw,
            claimed=ClaimedOut(
                title=claimed.title,
                year=claimed.claimed_year,
                date=claimed.claimed_date,
                reporter=claimed.reporter,
            ),
            status=citation.status.value,
            mismatches=citation.mismatches,
            unverified=citation.unverified,
            message=citation.message,
            case_id=citation.matched_case_id,
            source_url=official.source_url if official else None,
            case=CaseSummaryOut.from_entity(official) if official else None,
        )


class OpinionRefOut(BaseModel):
    kind: str
    author: str | None


class InsightsOut(BaseModel):
    """Findings parsed from the stored official text. Nothing here is generated."""

    case_id: int
    gr_no: str
    title: str | None
    source_url: str
    decision_date: date | None
    doc_type: DocTypeName
    division: str | None
    ponente: str | None
    disposition: DispositionName
    ruling: str | None
    concurring_justices: list[str]
    opinions: list[OpinionRefOut]
    statutes: list[StatuteOut]
    cited_cases: list[CitedCaseOut]
    footnote_count: int
    word_count: int
    attribution: Attribution = Attribution()

    @classmethod
    def from_insights(cls, i: CaseInsights) -> "InsightsOut":
        return cls(
            case_id=i.case_id,
            gr_no=i.gr_no,
            title=i.title,
            source_url=i.source_url,
            decision_date=i.decision_date,
            doc_type=i.doc_type.value,
            division=i.division,
            ponente=i.ponente,
            disposition=i.disposition.value,
            ruling=i.ruling,
            concurring_justices=i.concurring_justices,
            opinions=[OpinionRefOut(kind=o.kind, author=o.author) for o in i.opinions],
            statutes=[StatuteOut(type=s.statute_type.value, number=s.number, raw=s.raw) for s in i.statutes],
            cited_cases=[CitedCaseOut.from_entity(c, i.source_url) for c in i.cited_cases],
            footnote_count=i.footnote_count,
            word_count=i.word_count,
        )


class StatuteCountOut(BaseModel):
    statute_type: str
    number: str
    cases: int


class DispositionCountOut(BaseModel):
    year: int
    disposition: DispositionName
    cases: int


class CitedCaseCountOut(BaseModel):
    title: str
    gr_no: str | None
    cases: int


class PonenteCountOut(BaseModel):
    ponente: str
    cases: int


class TrendsOut(BaseModel):
    total_cases: int
    minimum_cases: int
    enough_data: bool
    message: str
    top_statutes: list[StatuteCountOut]
    dispositions_by_year: list[DispositionCountOut]
    most_cited_cases: list[CitedCaseCountOut]
    cases_per_ponente: list[PonenteCountOut]

    @classmethod
    def from_report(cls, r: TrendsReport) -> "TrendsOut":
        message = (
            f"{r.total_cases} stored decisions."
            if r.enough_data
            else f"Only {r.total_cases} stored decision(s): need at least {r.minimum_cases} before "
            "these counts say anything about patterns."
        )
        return cls(
            total_cases=r.total_cases,
            minimum_cases=r.minimum_cases,
            enough_data=r.enough_data,
            message=message,
            top_statutes=[StatuteCountOut(**vars(s)) for s in r.top_statutes],
            dispositions_by_year=[DispositionCountOut(**vars(d)) for d in r.dispositions_by_year],
            most_cited_cases=[CitedCaseCountOut(**vars(c)) for c in r.most_cited_cases],
            cases_per_ponente=[PonenteCountOut(**vars(p)) for p in r.cases_per_ponente],
        )


class UploadOut(BaseModel):
    id: int
    filename: str
    status: UploadStatusName
    created_at: datetime | None
    citations: list[CitationOut]
    attribution: Attribution = Attribution()

    @classmethod
    def from_report(cls, report: UploadReport) -> "UploadOut":
        upload = report.upload
        return cls(
            id=upload.id,
            filename=upload.filename,
            status=upload.status,
            created_at=upload.created_at,
            citations=[CitationOut.from_entity(c, report.cases) for c in upload.citations],
        )


class CatalogStatusOut(BaseModel):
    """How far the searchable copy of Lawphil's lists has got."""

    state: CatalogStateName
    entries: int
    months_read: int
    months_known: int
    percent: int

    @classmethod
    def from_entity(cls, s: CatalogStatus) -> "CatalogStatusOut":
        return cls(
            state=s.state,  # type: ignore[arg-type]
            entries=s.entries,
            months_read=s.months_read,
            months_known=s.months_known,
            percent=s.percent,
        )


class CatalogItemOut(BaseModel):
    """One decision on Lawphil's lists. Opening it saves the full case into the library."""

    title: str  # the parties, as Lawphil's list prints them
    gr_no: str  # the page's own number
    numbers: list[str]  # every number printed on the row
    also_decided_with: list[str]
    decision_date: date | None
    source_url: str
    case_id: int | None  # set when the case is already saved in the library
    in_library: bool

    @classmethod
    def from_hit(cls, hit: CatalogHit) -> "CatalogItemOut":
        e = hit.entry
        return cls(
            title=e.title,
            gr_no=str(e.gr_no),
            numbers=list(e.numbers),
            also_decided_with=list(e.also_decided_with),
            decision_date=e.decision_date,
            source_url=e.source_url,
            case_id=hit.case_id,
            in_library=hit.case_id is not None,
        )


class CatalogSearchOut(BaseModel):
    understood_as: CatalogUnderstoodAs
    items: list[CatalogItemOut]
    total: int
    limit: int
    offset: int
    catalog: CatalogStatusOut
    attribution: Attribution = Attribution()

    @classmethod
    def from_page(cls, page: CatalogPage, status: CatalogStatus) -> "CatalogSearchOut":
        return cls(
            understood_as=page.understood_as,  # type: ignore[arg-type]
            items=[CatalogItemOut.from_hit(h) for h in page.hits],
            total=page.total,
            limit=page.limit,
            offset=page.offset,
            catalog=CatalogStatusOut.from_entity(status),
        )


class CatalogBuildOut(BaseModel):
    started: bool  # False when a build was already running
    catalog: CatalogStatusOut
