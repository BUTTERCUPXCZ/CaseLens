"""Gemini, used only to POINT at where the Court states the Facts, Issue or Doctrine of a decision.

The model returns paragraph numbers, never text. The text a student sees is copied from the stored decision by code
(`SuggestCourtPassages`), so nothing the model writes can reach the digest."""
from caselens.application.ports.ai import PassageChecker, PassagePicker, PassageRequest
from caselens.domain.digest import CheckResult, Verdict
from caselens.infrastructure.ai.gemini_answerer import _GeminiCall
from caselens.infrastructure.config import Settings

PASSAGE_PROMPT_VERSION = "select-v1"

_PICKER_RULES = """You help a Philippine law student find where a Supreme Court decision ITSELF states certain parts of a case digest.
You are given numbered paragraphs of the decision ([P12] is paragraph 12). For each part requested, return the number of the
first and the last paragraph where the COURT states it, or null.
- Return paragraph numbers only. Never write, quote or paraphrase any text.
- Use only the paragraphs listed for that part. Pick consecutive paragraphs, as few as will do.
- FACTS: the Court's account of the events and of how the case came to the Court (the facts and the proceedings in the lower
  courts). Not the opening line that only says what petition is before the Court, and not the Court's discussion or analysis.
- ISSUE: where the Court states the question(s) it must decide, or the errors the petitioner raises, so a student can copy
  them. Not a lower court's reasoning, not an argument from the discussion.
- DOCTRINE: the paragraph(s) where the Court states the legal rule or principle it applies or lays down in this case (often
  "We hold", "It is settled", "The rule is"). Not a party's argument and not a summary of the facts.
- If the decision does not state the part, or you are not sure, return null. null is better than a guess."""

_RANGE = {
    "type": "object",
    "nullable": True,
    "properties": {"first": {"type": "integer"}, "last": {"type": "integer"}},
    "required": ["first", "last"],
}
_PICKER_SCHEMA = {
    "type": "object",
    "properties": {"facts": _RANGE, "issues": _RANGE, "doctrine": _RANGE},
}

_CHECKER_RULES = """You are a strict checker for a law-student tool. You get passages copied word for word from a Philippine
Supreme Court decision, each labelled with the part of a case digest it is meant to be. Judge each passage ONLY by its own words.
- supported: the passage really is the Court's statement of that part (FACTS: the Court's account of the events and proceedings;
  ISSUE: the Court's statement of the question(s) to be decided or the errors raised; DOCTRINE: the Court's statement of the
  legal rule it applies).
- partly_supported: it contains that part but mostly something else, or covers only a piece of it.
- not_supported: it is something else (introduction, a lower court's reasoning, a party's argument, the Court's ruling).
Be strict: when unsure, do not say supported. Give a short reason for any verdict that is not supported."""
_CHECKER_SCHEMA = {
    "type": "object",
    "properties": {
        "verdicts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "part": {"type": "string"},
                    "verdict": {"type": "string", "enum": [v.value for v in Verdict]},
                    "reason": {"type": "string"},
                },
                "required": ["part", "verdict", "reason"],
            },
        }
    },
    "required": ["verdicts"],
}
_WORDS = {"facts": "FACTS", "issues": "ISSUE", "doctrine": "DOCTRINE"}


class GeminiPassagePicker(PassagePicker):
    def __init__(self, settings: Settings, call: _GeminiCall | None = None) -> None:
        self._call = call or _GeminiCall(settings)
        self._model = settings.gemini_writer_model

    def pick(self, request: PassageRequest) -> dict[str, tuple[int, int] | None]:
        blocks = []
        for key in request.keys:
            passages = "\n".join(f"[{p.id}] {p.text}" for p in request.candidates[key])
            blocks.append(f"PART: {_WORDS[key]}\nPARAGRAPHS YOU MAY USE FOR THIS PART:\n{passages}")
        data = self._call.json(self._model, _PICKER_RULES, "\n\n".join(blocks), _PICKER_SCHEMA)
        picked: dict[str, tuple[int, int] | None] = {}
        for key in request.keys:
            item = data.get(key)
            picked[key] = (int(item["first"]), int(item["last"])) if isinstance(item, dict) and "first" in item and "last" in item else None
        return picked


class GeminiPassageChecker(PassageChecker):
    def __init__(self, settings: Settings, call: _GeminiCall | None = None) -> None:
        self._call = call or _GeminiCall(settings)
        self._model = settings.gemini_checker_model

    def check(self, passages: dict[str, str]) -> dict[str, CheckResult]:
        blocks = [f"PART: {_WORDS[key]}\nPASSAGE:\n{text}" for key, text in passages.items()]
        data = self._call.json(self._model, _CHECKER_RULES, "\n\n".join(blocks), _CHECKER_SCHEMA)
        by_part = {str(item["part"]).strip().upper(): CheckResult(Verdict(item["verdict"]), item.get("reason", "")) for item in data.get("verdicts", [])}
        # A part the checker did not rule on is NOT confirmed: silence is never approval.
        return {key: by_part.get(_WORDS[key], CheckResult(Verdict.NOT_SUPPORTED, "the checker gave no verdict")) for key in passages}
