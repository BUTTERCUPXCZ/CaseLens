"""The digest in the client's format: sections of blocks of cited sentences. Every sentence points at the decision's
paragraphs; a sentence that could not be backed is never in here."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from caselens.domain.digest import AnswerSentence


class Section(str, Enum):
    DOCTRINE = "doctrine"
    FACTS = "facts"
    ARGUMENTS_PETITIONERS = "arguments_petitioners"
    ARGUMENTS_RESPONDENTS = "arguments_respondents"
    ISSUE = "issue"
    RULING = "ruling"
    RATIO = "ratio"
    DISSENTS = "dissents"
    TOPIC = "topic"
    WHY = "why"
    CASE_SUMMARY = "case_summary"  # one paragraph of facts, issue and ruling: first in the short download and the full digest


SECTION_TITLES: dict[Section, str] = {
    Section.DOCTRINE: "Doctrine",
    Section.FACTS: "Facts",
    Section.ARGUMENTS_PETITIONERS: "Petitioners’ arguments",
    Section.ARGUMENTS_RESPONDENTS: "Respondents’ arguments",
    Section.ISSUE: "Issue",
    Section.RULING: "Ruling",
    Section.RATIO: "Ratio Decidendi",
    Section.DISSENTS: "The Dissents (useful for recitation)",
    Section.TOPIC: "Topic Explained",
    Section.WHY: "Why This Case Matters",
    Section.CASE_SUMMARY: "Case Summary",
}


class Level(str, Enum):
    """What a student downloads. One digest is written once; a level only chooses which sections are printed."""

    SHORT = "short"  # Case Summary and Doctrine
    STANDARD = "standard"  # Doctrine, Facts, Issue, Ruling (1 to 2 pages)
    FULL = "full"  # the full case digest (about 6 pages)


LEVEL_SECTIONS: dict[Level, tuple[Section, ...]] = {
    Level.SHORT: (Section.CASE_SUMMARY, Section.DOCTRINE),  # the client's order: the summary first
    Level.STANDARD: (Section.DOCTRINE, Section.FACTS, Section.ARGUMENTS_PETITIONERS, Section.ARGUMENTS_RESPONDENTS, Section.ISSUE, Section.RULING),
    Level.FULL: (Section.CASE_SUMMARY, *(s for s in Section if s is not Section.CASE_SUMMARY)),  # also what the case page shows
}
# A digest written before the Case Summary existed (or whose summary did not pass the checks) prints these in its place
_SUMMARY_STAND_IN = (Section.FACTS, Section.ISSUE, Section.RULING)


@dataclass(frozen=True)
class DigestBlock:
    sentences: tuple[AnswerSentence, ...]
    heading: str | None = None
    as_list: bool = False  # bullet points instead of a paragraph


@dataclass
class DigestDraft:
    sections: dict[Section, tuple[DigestBlock, ...]] = field(default_factory=dict)

    def sentences(self) -> list[AnswerSentence]:
        return [s for blocks in self.sections.values() for block in blocks for s in block.sentences]


def sections_for(level: Level, draft: DigestDraft) -> tuple[Section, ...]:
    """The sections a level prints for this digest. Without a Case Summary, the short level prints Facts, Issue and Ruling instead (so it
    is never only a Doctrine); the full digest already has them and simply starts with the Doctrine."""
    wanted = LEVEL_SECTIONS[level]
    if Section.CASE_SUMMARY in wanted and not draft.sections.get(Section.CASE_SUMMARY):
        at = wanted.index(Section.CASE_SUMMARY)
        wanted = wanted[:at] + tuple(s for s in _SUMMARY_STAND_IN if s not in wanted) + wanted[at + 1:]
    return wanted


class DigestState(str, Enum):
    PENDING = "pending"  # queued or being written
    READY = "ready"
    FAILED = "failed"  # the writer could not finish; `error` says why in plain words


class DigestStage(str, Enum):
    """Where a PENDING digest is, for the progress bar. Cleared once the digest is ready or failed."""

    QUEUED = "queued"  # waiting for a free worker
    WRITING = "writing"  # the writer call: the long part
    CHECKING = "checking"  # the second model judges the flagged and key sentences
    REPAIRING = "repairing"  # failed sentences are rewritten from their own paragraphs and judged again


MAX_SCOPE = 300


def clean_scope(text: str | None) -> str:
    """The scope as it is kept and shown: spaces tidied, at most 300 characters."""
    return " ".join((text or "").split())[:MAX_SCOPE]


def scope_key(text: str | None) -> str:
    """Two scopes that differ only in capitals or spaces are the same digest."""
    return clean_scope(text).lower()


@dataclass
class CaseDigestV2:
    """The case digest of one MAIN case for one topic scope, written once and kept. Not tied to an upload: everyone sees it.
    `scope` "" is the standard digest; a scope ("Presidential powers") is a digest focused on that doctrine or issue."""

    case_id: int
    scope: str = ""
    state: DigestState = DigestState.PENDING
    draft: DigestDraft = field(default_factory=DigestDraft)
    written: int = 0  # sentences the writer produced
    dropped: int = 0  # sentences that did not pass the checks and are not in the digest
    error: str | None = None
    model: str | None = None
    prompt_version: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    stage: DigestStage | None = None  # while PENDING: the step it is on
    stage_at: datetime | None = None  # when that step began
    id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def scope_key(self) -> str:
        return scope_key(self.scope)

    def is_current(self, version: str) -> bool:
        """Written by the current prompt and checking pipeline (`version`, kept in `prompt_version`)? An older one is still served:
        it is the cached digest until someone asks for it to be written again."""
        return self.prompt_version == version


@dataclass(frozen=True)
class DigestHeader:
    """The lines at the top of a digest: what the client's sample shows under "CASE DIGEST"."""

    case_name: str  # "Marcos v. Manglapus"
    citation: str  # "G.R. No. 88211, September 15, 1989 (En Banc)"
    topic: str | None  # the subject
    ponente: str | None
