"""Ports for the AI that answers the questions in a digest. Facts, Issue, Ruling and Doctrine never come
from here: they are the Court's own text. The AI only writes explanations, and only from the sources given.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass

from caselens.domain.digest import AnswerSentence, CheckResult, SourcePassage


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
