"""HTTP shapes for case digests."""
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from caselens.domain.case_digest import CaseDigest, DigestField
from caselens.domain.entities import Case
from caselens.presentation.api.schemas import Attribution

FieldKindName = Literal["verbatim", "answer", "note"]
FieldOriginName = Literal[
    "court_heading", "court_ruling", "student_picked", "student_pasted", "ai_drafted", "student_written", "empty"
]
FieldStateName = Literal["ready", "pending", "unavailable"]
DigestStatusName = Literal["pending", "ready", "failed"]
TemplateName = Literal["facts_and_doctrine", "full"]


class PassageOut(BaseModel):
    first: int
    last: int


class DigestFieldOut(BaseModel):
    key: str
    label: str
    kind: FieldKindName
    text: str
    origin: FieldOriginName
    state: FieldStateName
    cites: list[str]  # P12 = paragraph 12 of the decision; S1 = a passage the student pasted; R1 = the reviewer's own
    passage: PassageOut | None
    question: str | None
    note: str | None  # plain-words reason a field is empty or cut short
    edited: bool
    can_reset: bool  # the system's version can be put back

    @classmethod
    def from_entity(cls, item: DigestField) -> "DigestFieldOut":
        return cls(
            key=item.key,
            label=item.label,
            kind=item.kind.value,
            text=item.text,
            origin=item.origin.value,
            state=item.state.value,
            cites=list(item.cites),
            passage=None if item.passage is None else PassageOut(first=item.passage.first, last=item.passage.last),
            question=item.question,
            note=item.note,
            edited=item.edited,
            can_reset=item.original is not None,
        )


class DigestOut(BaseModel):
    id: int
    case_id: int
    upload_id: int | None
    template: TemplateName
    status: DigestStatusName
    error: str | None
    # the header line of the box, from the stored decision
    case_title: str | None
    gr_no: str
    decision_date: date | None
    source_url: str
    fields: list[DigestFieldOut]
    pickable_first: int | None  # paragraphs of the decision a student may pick from
    pickable_last: int | None
    attribution: Attribution = Attribution()

    @classmethod
    def from_entity(cls, digest: CaseDigest, case: Case, pickable: tuple[int, int] | None) -> "DigestOut":
        return cls(
            id=digest.id,
            case_id=digest.case_id,
            upload_id=digest.upload_id,
            template=digest.template.value,
            status=digest.status.value,
            error=digest.error,
            case_title=case.title,
            gr_no=case.gr_no.value,
            decision_date=case.decision_date,
            source_url=case.source_url,
            fields=[DigestFieldOut.from_entity(f) for f in digest.fields],
            pickable_first=None if pickable is None else pickable[0],
            pickable_last=None if pickable is None else pickable[1],
        )


class DigestRequestIn(BaseModel):
    upload_id: int | None = None
    template: TemplateName = "full"
    questions: list[str] = Field(default_factory=list, max_length=10)


class TextIn(BaseModel):
    text: str


class PassageIn(BaseModel):
    first: int
    last: int


class QuestionIn(BaseModel):
    question: str


class RegenerateIn(BaseModel):
    keys: list[str] = Field(min_length=1, max_length=20)
