import logging
import re
from dataclasses import dataclass, field

from caselens.application.ports.ai import PassageChecker, PassagePicker, PassageRequest
from caselens.domain.digest import ParagraphRange, SourcePassage, Verdict
from caselens.domain.services.digest_field_factory import DigestFieldFactory
from caselens.domain.services.passage_suggester import Suggestion
from caselens.domain.services.passage_validator import PassageValidator

logger = logging.getLogger(__name__)

PICKED_BY_AI = "pointed at by an AI, copied from the decision, confirmed by a second check"
_FACTS_ISSUE_WINDOW = 80  # paragraphs from the start of the body that Facts and Issue may come from
_LONG_DECISION = 250  # above this, Doctrine candidates are only the paragraphs that sound like a rule
_PREVIEW = {"facts": 600, "issues": 600, "doctrine": 300}
_RULE_CUES = re.compile(
    r"\bwe (?:hold|rule|declare|reiterate|resolve)\b|\bit is (?:a )?(?:well-?)?settled\b|\bthe (?:rule|doctrine|principle) (?:is|that)\b|"
    r"\bis the (?:rule|doctrine|principle)\b|\bwe have (?:held|ruled)\b|\bgeneral rule\b",
    re.IGNORECASE,
)
_CHECKED_TEXT_CHARS = 3500
# The Court's first line often only says which petition is before it. That is the introduction, not the facts.
_INTRO = re.compile(
    r"^(?:challenged|assailed|questioned|before (?:us|the court|this court)|for (?:the |our )?(?:court'?s |our )?"
    r"(?:resolution|review|consideration|disposition) (?:is|are)|this (?:is an? |petition|appeal)|petitioners? seeks?|"
    r"these (?:consolidated )?petitions)\b",
    re.IGNORECASE,
)
_ABOUT_THE_PETITION = re.compile(r"\b(?:petition|appeal|certiorari|mandamus|rule \d+)\b", re.IGNORECASE)
# Where the facts stop and the party's argument (the issue) begins: "In this petition, petitioner contends that ...".
_ARGUMENT_STARTS = re.compile(
    r"^(?:(?:in|with) (?:the|this) (?:instant |present )?(?:petition|appeal)[^.]{0,60}\b|petitioners? (?:now )?)"
    r"(?:contends?|argues?|raises?|submits?|insists?|assails?|alleges?|claims?)\b",
    re.IGNORECASE,
)


@dataclass
class PassageSuggestions:
    found: dict[str, Suggestion] = field(default_factory=dict)
    not_found: dict[str, str] = field(default_factory=dict)  # key -> why nothing was suggested (for the log)


class SuggestCourtPassages:
    """Finds where the Court itself states the Facts, the Issue or the Doctrine, for a decision the rules could not read.

    The AI only points: it returns paragraph numbers. Code then (1) checks the numbers (inside the body, few, contiguous,
    among the paragraphs offered), (2) copies the Court's exact paragraphs from the stored decision, and (3) asks a second
    model whether that copied text really is the statement asked for. Only a clear "yes" is used; otherwise nothing is
    suggested, because a wrong passage is worse than an empty box.
    """

    def __init__(self, picker: PassagePicker, checker: PassageChecker, validator: PassageValidator | None = None) -> None:
        self._picker = picker
        self._checker = checker
        self._validator = validator or PassageValidator()

    def execute(self, keys: list[str], paragraphs: list[str], body_start: int | None, ruling: ParagraphRange | None) -> PassageSuggestions:
        result = PassageSuggestions()
        if body_start is None or ruling is None or ruling.first <= body_start:
            result.not_found = {key: "no readable body to look in" for key in keys}
            return result
        allowed = ParagraphRange(body_start, ruling.first - 1)
        candidates = {key: self._candidates(key, paragraphs, allowed) for key in keys}
        request = PassageRequest(
            tuple(keys),
            {key: tuple(SourcePassage(f"P{i}", self._preview(key, paragraphs[i])) for i in sorted(indexes)) for key, indexes in candidates.items()},
        )
        picked = self._picker.pick(request)  # may raise AiUnavailableError: the caller settles that

        copied: dict[str, tuple[ParagraphRange, str]] = {}
        for key in keys:
            pair = picked.get(key)
            if pair is None:
                result.not_found[key] = "the decision does not state it, or the AI could not tell"
                continue
            try:
                rng = ParagraphRange(*pair)
            except ValueError:
                result.not_found[key] = f"invalid range {pair}"
                continue
            problem = self._validator.check(key, rng, allowed, candidates[key], paragraphs)
            if problem:
                result.not_found[key] = problem
                continue
            if key == "facts":
                rng = self._tidy_facts(paragraphs, rng)
            text, _, _ = DigestFieldFactory.verbatim_text(paragraphs, rng)
            copied[key] = (rng, text)

        if copied:
            verdicts = self._checker.check({key: text[:_CHECKED_TEXT_CHARS] for key, (_, text) in copied.items()})
            for key, (rng, _) in copied.items():
                verdict = verdicts.get(key)
                if verdict is not None and verdict.verdict is Verdict.SUPPORTED:
                    result.found[key] = Suggestion(rng, PICKED_BY_AI)
                else:
                    why = f"{verdict.verdict.value}: {verdict.reason}" if verdict else "no verdict"
                    result.not_found[key] = f"the second check did not agree ({why[:160]})"
        for key, why in result.not_found.items():
            logger.info("no %s suggested: %s", key, why)
        return result

    @staticmethod
    def _tidy_facts(paragraphs: list[str], rng: ParagraphRange) -> ParagraphRange:
        """Plain code, no AI: leave out the opening line that only announces the petition, and stop where the party's
        argument starts. Both are the Court's words, but they are not the facts."""
        first, last = rng.first, rng.last
        while first < last and _INTRO.search(paragraphs[first].strip()[:200]) and _ABOUT_THE_PETITION.search(paragraphs[first][:250]) and len(paragraphs[first]) < 800:
            first += 1
        for index in range(first + 1, last + 1):
            if _ARGUMENT_STARTS.search(paragraphs[index].strip()[:200]):
                last = index - 1
                break
        return ParagraphRange(first, last)

    @staticmethod
    def _candidates(key: str, paragraphs: list[str], allowed: ParagraphRange) -> set[int]:
        indexes = [i for i in allowed.indexes() if paragraphs[i].strip()]
        if key in ("facts", "issues"):
            return {i for i in indexes if i < allowed.first + _FACTS_ISSUE_WINDOW}
        if len(indexes) > _LONG_DECISION:
            return {i for i in indexes if _RULE_CUES.search(paragraphs[i][:400])}
        return set(indexes)

    @staticmethod
    def _preview(key: str, text: str) -> str:
        limit = _PREVIEW[key]
        plain = " ".join(text.split())
        return plain if len(plain) <= limit else plain[:limit].rstrip() + " ..."
