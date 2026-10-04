"""Value objects for reading a decision paragraph by paragraph.

A decision is stored as paragraphs joined by newlines (`Case.full_text`). A paragraph is identified by its
position in that list, so anything built on top (a digest, an AI pick) can only point at paragraphs that
exist, and the text shown is always the stored text.
"""
from dataclasses import dataclass, field
from enum import Enum


class SectionKind(str, Enum):
    FACTS = "facts"
    ISSUES = "issues"


@dataclass(frozen=True)
class Paragraph:
    index: int
    text: str


@dataclass(frozen=True)
class ParagraphRange:
    """Paragraph indexes `first` to `last`, both included."""

    first: int
    last: int

    def __post_init__(self) -> None:
        if self.first < 0 or self.last < self.first:
            raise ValueError(f"Invalid paragraph range {self.first}-{self.last}")

    def __len__(self) -> int:
        return self.last - self.first + 1

    def indexes(self) -> range:
        return range(self.first, self.last + 1)


@dataclass(frozen=True)
class SourcePassage:
    """A piece of text an answer may rest on. `id` is what an answer cites: `P12` is paragraph 12 of the
    decision, `S1` a passage the student pasted or selected, `R1` the reviewer's own passage."""

    id: str
    text: str


@dataclass(frozen=True)
class AnswerSentence:
    text: str
    cites: tuple[str, ...]


class Verdict(str, Enum):
    SUPPORTED = "supported"
    PARTLY = "partly_supported"
    NOT_SUPPORTED = "not_supported"


@dataclass(frozen=True)
class CheckResult:
    verdict: Verdict
    reason: str = ""


@dataclass(frozen=True)
class DroppedSentence:
    text: str
    reason: str


@dataclass(frozen=True)
class GroundedAnswer:
    """An answer to one question in the digest ("Topic explained", "Why this case matters", or a question
    from the student's own reviewer). Only sentences that passed every check are in `sentences`."""

    question: str
    sentences: tuple[AnswerSentence, ...]
    dropped: tuple[DroppedSentence, ...] = field(default_factory=tuple)

    @property
    def abstained(self) -> bool:
        return not self.sentences
