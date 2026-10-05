"""The digest box a student fills for one cited case: header, then fields (Facts, Issue, Ruling, Doctrine,
Topic explained, Why this case matters, and any question of their own).

Court text is never rewritten. A verbatim field holds the Court's own paragraphs (picked by the Court's
heading or by the student) or text the student pasted; an answer field holds sentences that passed the
checks in `AnswerCaseQuestion`. The student can edit any field; the original is kept so it can be restored.
"""
from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import Enum


class FieldKind(str, Enum):
    VERBATIM = "verbatim"  # the Court's own words, or a passage the student pasted
    ANSWER = "answer"  # an explanation written from the decision, every sentence cited
    NOTE = "note"  # the student's own writing from the start


class FieldOrigin(str, Enum):
    COURT_HEADING = "court_heading"  # found under the Court's own heading ("The Facts")
    COURT_RULING = "court_ruling"  # the paragraphs before the final SO ORDERED
    COURT_SUGGESTED = "court_suggested"  # the Court's own paragraphs, found for the student (rules or an AI that only points): check them
    STUDENT_PICKED = "student_picked"  # paragraphs of the decision the student chose
    STUDENT_PASTED = "student_pasted"  # text the student pasted (not checked against the decision)
    AI_DRAFTED = "ai_drafted"  # sentences from the answerer that passed every check
    STUDENT_WRITTEN = "student_written"  # typed or edited by the student
    EMPTY = "empty"


class FieldState(str, Enum):
    READY = "ready"
    PENDING = "pending"  # an answer is still being written
    UNAVAILABLE = "unavailable"  # nothing to show; `note` says why


class DigestStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    FAILED = "failed"


class DigestTemplate(str, Enum):
    FACTS_AND_DOCTRINE = "facts_and_doctrine"  # "Digest 1" in the student's reviewer
    FULL = "full"  # "Digest 2": facts, issue, ruling, doctrine, topic explained, why it matters


# The questions the AI answers for the two standard fields (the student's words in the reviewer).
TOPIC_KEY, WHY_KEY = "topic", "why"
STANDARD_QUESTIONS = {
    TOPIC_KEY: ("Topic explained", "Explain the topic of this case accurately, in plain words."),
    WHY_KEY: ("Why this case matters", "Why does this case matter? Say what the Court decided and what follows from it."),
}


@dataclass(frozen=True)
class Passage:
    """A run of the decision's paragraphs (positions in the stored text, both ends included)."""

    first: int
    last: int


@dataclass(frozen=True)
class DigestField:
    key: str
    label: str
    kind: FieldKind
    text: str = ""
    origin: FieldOrigin = FieldOrigin.EMPTY
    state: FieldState = FieldState.READY
    cites: tuple[str, ...] = ()  # sources an answer rests on (P12 = paragraph 12 of the decision)
    passage: Passage | None = None  # for verbatim text taken from the decision
    question: str | None = None  # for answer fields
    note: str | None = None  # why a field is empty or unavailable, in plain words
    edited: bool = False
    original: "DigestField | None" = None  # what the system produced, for "reset to the Court's text"
    reason: str | None = None  # for the audit log: why this passage was suggested ("cue: ...", "picked by the AI, confirmed by a second check")

    def edited_to(self, text: str, origin: FieldOrigin, passage: Passage | None = None) -> "DigestField":
        base = self.original or replace(self, original=None)
        return replace(
            self,
            text=text,
            origin=origin,
            passage=passage,
            cites=(),
            state=FieldState.READY,
            note=None,
            edited=True,
            original=base,
        )

    def reset(self) -> "DigestField":
        return self.original if self.original is not None else self


@dataclass
class CaseDigest:
    case_id: int
    template: DigestTemplate
    upload_id: int | None = None
    status: DigestStatus = DigestStatus.PENDING
    fields: list[DigestField] = field(default_factory=list)
    error: str | None = None
    model: str | None = None
    prompt_version: str | None = None
    parser_version: int | None = None
    ai_answered_at: datetime | None = None
    id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def field_named(self, key: str) -> DigestField | None:
        return next((f for f in self.fields if f.key == key), None)

    def replace_field(self, updated: DigestField) -> None:
        self.fields = [updated if f.key == updated.key else f for f in self.fields]
