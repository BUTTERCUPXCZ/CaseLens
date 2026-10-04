from caselens.application.ports.ai import AnswerChecker, AnswerRequest, AnswerWriter
from caselens.domain.digest import (
    AnswerSentence,
    DroppedSentence,
    GroundedAnswer,
    SourcePassage,
    Verdict,
)
from caselens.domain.services.answer_validator import AnswerValidator


class AnswerCaseQuestion:
    """Answers one question of the digest ("Why does this case matter?") from the sources it is given.

    The AI drafts; code and a second AI call decide what survives:
      1. every sentence must cite sources that exist, and any number or name in it must be in those sources;
      2. a separate checker must mark the sentence SUPPORTED by the passages it cites.
    Whatever fails is dropped and recorded (so the student can see why). If nothing survives, the answer is
    empty: "not enough in the decision to say", never a weaker guess.
    """

    def __init__(self, writer: AnswerWriter, checker: AnswerChecker, validator: AnswerValidator | None = None) -> None:
        self._writer = writer
        self._checker = checker
        self._validator = validator or AnswerValidator()

    def answer(self, request: AnswerRequest) -> GroundedAnswer:
        sources = {source.id: source for source in request.sources}
        drafted = self._writer.write(request)[: request.max_sentences]

        dropped: list[DroppedSentence] = []
        candidates: list[AnswerSentence] = []
        for sentence in drafted:
            problem = self._validator.check(sentence, sources, request.question)
            if problem:
                dropped.append(DroppedSentence(sentence.text, problem))
            else:
                candidates.append(sentence)

        kept: list[AnswerSentence] = []
        if candidates:
            for sentence, result in zip(candidates, self._checker.check(candidates, sources), strict=True):
                if result.verdict is Verdict.SUPPORTED:
                    kept.append(sentence)
                else:
                    reason = f"checker: {result.verdict.value}" + (f" ({result.reason})" if result.reason else "")
                    dropped.append(DroppedSentence(sentence.text, reason))
        return GroundedAnswer(request.question, tuple(kept), tuple(dropped))


def decision_sources(paragraphs: list[str], first: int, last: int, max_chars: int = 2500) -> list[SourcePassage]:
    """The decision's body paragraphs as citable sources `P<index>` (index = position in the stored text)."""
    return [
        SourcePassage(f"P{i}", paragraphs[i] if len(paragraphs[i]) <= max_chars else paragraphs[i][:max_chars] + " ...")
        for i in range(first, last + 1)
    ]
