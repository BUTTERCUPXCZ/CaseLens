"""Ports for the AI that answers the questions in a digest. Facts, Issue, Ruling and Doctrine never come
from here: they are the Court's own text. The AI only writes explanations, and only from the sources given.
"""
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass

from caselens.domain.digest import AnswerSentence, CheckResult, SourcePassage
from caselens.domain.digest_v2 import DigestDraft


@dataclass(frozen=True)
class AnswerRequest:
    question: str
    sources: tuple[SourcePassage, ...]
    max_sentences: int = 3


class AnswerWriter(ABC):
    @abstractmethod
    def write(self, request: AnswerRequest) -> list[AnswerSentence]:
        """Draft the answer, every sentence citing source ids. An empty list means "the sources do not say".
        Raises AiUnavailableError when the service cannot be reached."""


class AnswerChecker(ABC):
    @abstractmethod
    def check(self, sentences: list[AnswerSentence], sources: dict[str, SourcePassage]) -> list[CheckResult]:
        """One result per sentence, judged only against the passages that sentence cites."""


@dataclass(frozen=True)
class PassageRequest:
    """Which parts of the digest to find in the decision, and the paragraphs each may point at (previews only)."""

    keys: tuple[str, ...]  # "facts", "issues", "doctrine"
    candidates: dict[str, tuple[SourcePassage, ...]]  # per key, ids `P<index>`


class PassagePicker(ABC):
    """Points at where the COURT states a part of the digest. It returns paragraph numbers, never text: what the
    student sees is copied from the stored decision by code, so this cannot put a word of its own into the digest."""

    @abstractmethod
    def pick(self, request: PassageRequest) -> dict[str, tuple[int, int] | None]:
        """For each requested key, the first and last paragraph index, or None if the decision does not state it.
        Raises AiUnavailableError when the service cannot be reached."""


class PassageChecker(ABC):
    @abstractmethod
    def check(self, passages: dict[str, str]) -> dict[str, CheckResult]:
        """A second model reads the copied text of each part ("issues" -> the paragraphs picked) and says whether it
        really is the Court's statement of that part. Only `supported` is accepted."""


@dataclass(frozen=True)
class DigestRequest:
    """Everything the digest writer may use: the decision's numbered passages and a few facts from the case record."""

    sources: tuple[SourcePassage, ...]  # P<i> = paragraph i of the decision, O<n>.<i> = paragraph i of separate opinion n
    case_line: str  # "Marcos v. Manglapus, G.R. No. 88211, September 15, 1989 (En Banc), ponente Cortes, J."
    subject: str | None = None  # the student's tags ("Constitutional Law, Political Law"), when given
    opinions: tuple[str, ...] = ()  # "O1: Fernan, C.J., concurring"
    scope: str = ""  # the topic scope the student asked for ("Presidential powers"); "" = the standard digest


class DigestWriter(ABC):
    @abstractmethod
    def write(self, request: DigestRequest) -> DigestDraft:
        """Draft every section of the digest, each sentence citing passage ids. Raises AiUnavailableError."""

    @abstractmethod
    def repair(self, request: DigestRequest, failed: list[tuple[str, str, str]]) -> dict[int, AnswerSentence]:
        """Rewrite sentences that did not pass (section, text, reason) so each says only what its cited passages say, or leave
        it out. Returns the replacements by the position of the failed sentence in `failed`. Raises AiUnavailableError."""
