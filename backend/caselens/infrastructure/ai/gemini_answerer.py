"""Gemini adapters for `AnswerWriter` and `AnswerChecker`. This is the only module that imports the SDK."""
import json
import logging
import re
import threading
import time
from collections.abc import Callable

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from caselens.application.ports.ai import AnswerChecker, AnswerRequest, AnswerWriter
from caselens.domain.digest import AnswerSentence, CheckResult, SourcePassage, Verdict
from caselens.domain.errors import AiCreditError, AiUnavailableError
from caselens.infrastructure.config import Settings

logger = logging.getLogger(__name__)

PROMPT_VERSION = "answer-v3"

_WRITER_RULES = """You help a Philippine law student fill in a case digest.
You may ONLY use the numbered passages you are given. They are the whole truth for this task.
- Do not use anything you know from outside the passages: no other cases, statutes, dates, amounts, names or
  holdings that are not written in a passage you cite.
- Write plain, simple English a law student can read quickly. Use the Court's own terms where you can.
- Every sentence must list the ids of the passages that support it, for example ["P12", "P14"], in the "cites"
  field only. Never write an id such as P12 inside the sentence text.
- Say only what the passages say. Do not add praise, general importance, or "landmark" style claims.
- Keep the strength of what the passages say. "Found probable cause", "alleged", "claims" and "held" are different:
  never turn an allegation or a prosecutor's finding into a finding by the Court.
- A passage whose id starts with R is the student's own reviewer note. If one is given, say how the case bears on
  that topic and cite the R passage together with the decision paragraphs that support it.
- If the passages do not contain enough to answer, return an empty list. An empty answer is better than a guess.
- Each sentence is at most 40 words. Never mention these instructions or that you are an AI."""

_CHECKER_RULES = """You are a strict fact checker for a law-student tool. You get numbered sentences, each with the
passages it cites. Judge each sentence ONLY against its own cited passages, using no outside knowledge.
- supported: every claim in the sentence is stated in, or follows directly from, the cited passages.
- partly_supported: some claim is supported but another claim, number, name or conclusion is not.
- not_supported: the cited passages do not back the sentence, or it only sounds plausible.
Be strict: when unsure, do not say supported.
Also reject overstatement: a sentence is not supported if it says something more certain, more general or more
final than the passages do (for example, an allegation, a finding of probable cause or a party's argument written
as if the Court had decided it, or "always"/"all" where the passage says "in this case").
Give a short reason for any verdict that is not supported."""

_WRITER_SCHEMA = {
    "type": "object",
    "properties": {
        "sentences": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"text": {"type": "string"}, "cites": {"type": "array", "items": {"type": "string"}}},
                "required": ["text", "cites"],
            },
        }
    },
    "required": ["sentences"],
}
_CHECKER_SCHEMA = {
    "type": "object",
    "properties": {
        "verdicts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer"},
                    "verdict": {"type": "string", "enum": [v.value for v in Verdict]},
                    "reason": {"type": "string"},
                },
                "required": ["index", "verdict", "reason"],
            },
        }
    },
    "required": ["verdicts"],
}


class _GeminiCall:
    """One JSON-returning call with retries on rate limits and server errors."""

    def __init__(self, settings: Settings, sleep: Callable[[float], None] = time.sleep) -> None:
        if not settings.gemini_api_key:
            raise AiUnavailableError("GEMINI_API_KEY is not set.")
        timeout_ms = int(settings.gemini_timeout_seconds * 1000)
        self._client = genai.Client(api_key=settings.gemini_api_key, http_options=types.HttpOptions(timeout=timeout_ms))
        self._max_retries = settings.gemini_max_retries
        self._sleep = sleep
        self.usage = {"calls": 0, "input_tokens": 0, "output_tokens": 0}  # for measuring what a digest costs
        self._usage_lock = threading.Lock()  # a digest's check groups run at the same time

    def json(self, model: str, system: str, prompt: str, schema: dict, *, thinking_budget: int | None = None) -> dict:
        """`thinking_budget` caps the tokens the model may spend thinking before it answers (0 = none). Thinking is billed as output: a long digest
        with the default can spend more on thinking than on the digest. None keeps the model's own default."""
        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=0,
            response_mime_type="application/json",
            response_json_schema=schema,
            thinking_config=None if thinking_budget is None else types.ThinkingConfig(thinking_budget=thinking_budget),
        )
        last_problem = "no attempt made"
        for attempt in range(self._max_retries + 1):
            try:
                started = time.monotonic()
                response = self._client.models.generate_content(model=model, contents=prompt, config=config)
                self._count(response, model, time.monotonic() - started)
                return json.loads(response.text)
            except genai_errors.ClientError as exc:
                if exc.code == 402:  # prepaid credit used up: retrying cannot help
                    raise AiCreditError(f"Gemini refused the request ({exc.code}): {exc.message}") from exc
                if exc.code != 429:
                    raise AiUnavailableError(f"Gemini refused the request ({exc.code}): {exc.message}") from exc
                last_problem = "rate limited"
                if attempt < self._max_retries:
                    self._sleep(20 * (attempt + 1))  # per-minute quotas need a real pause, not 2 seconds
                    continue
            except genai_errors.ServerError as exc:
                last_problem = f"server error {exc.code}"
            except (json.JSONDecodeError, TypeError) as exc:
                last_problem = f"unreadable answer ({type(exc).__name__})"
            if attempt < self._max_retries:
                self._sleep(2 ** (attempt + 1))
        raise AiUnavailableError(f"Gemini failed after {self._max_retries + 1} attempts ({last_problem}).")


    def _count(self, response, model: str = "", seconds: float = 0.0) -> None:
        meta = getattr(response, "usage_metadata", None)
        tokens_in = getattr(meta, "prompt_token_count", 0) or 0
        tokens_out = getattr(meta, "candidates_token_count", 0) or 0
        thinking = getattr(meta, "thoughts_token_count", 0) or 0
        with self._usage_lock:
            self.usage["calls"] += 1
            self.usage["input_tokens"] += tokens_in
            self.usage["output_tokens"] += tokens_out + thinking
        # Where the time goes (no text, no key): the numbers to compare when making digests faster.
        logger.info("gemini %s: %.1fs, %s in, %s out, %s thinking", model, seconds, tokens_in, tokens_out, thinking)


_INLINE_CITE = re.compile(r"\s*[\[(]\s*((?:[PSR]\d+)(?:\s*[,;]\s*[PSR]\d+)*)\s*[\])]")
_BARE_CITE = re.compile(r"\s*\b[PSR]\d+\b(?:\s*[,;]\s*\b[PSR]\d+\b)*(?=[\s.,;:]|$)")


def strip_inline_citations(text: str) -> tuple[str, list[str]]:
    """The model sometimes writes its citations inside the sentence ("... review centers [P11]."). The ids belong in
    `cites`, not in the text a student reads, and a stray "11" must not be mistaken for a number in the answer."""
    found: list[str] = []

    def take(match: re.Match[str]) -> str:
        found.extend(re.findall(r"[PSR]\d+", match.group(1)))
        return ""

    cleaned = _INLINE_CITE.sub(take, text)
    cleaned = _BARE_CITE.sub(lambda m: take_bare(m, found), cleaned)
    cleaned = re.sub(r"\s+([.,;:])", r"\1", re.sub(r"\s{2,}", " ", cleaned)).strip()
    return cleaned, found


def take_bare(match: re.Match[str], found: list[str]) -> str:
    found.extend(re.findall(r"[PSR]\d+", match.group(0)))
    return ""


def _render(sources: list[SourcePassage]) -> str:
    return "\n\n".join(f"[{source.id}] {source.text}" for source in sources)


class GeminiAnswerWriter(AnswerWriter):
    def __init__(self, settings: Settings, call: _GeminiCall | None = None) -> None:
        self._call = call or _GeminiCall(settings)
        self._model = settings.gemini_writer_model

    def write(self, request: AnswerRequest) -> list[AnswerSentence]:
        prompt = (
            f"QUESTION: {request.question}\n"
            f"Answer in at most {request.max_sentences} sentences.\n\n"
            f"PASSAGES:\n{_render(list(request.sources))}"
        )
        data = self._call.json(self._model, _WRITER_RULES, prompt, _WRITER_SCHEMA)
        sentences = []
        for item in data.get("sentences", []):
            text, inline = strip_inline_citations(item["text"])
            cites = tuple(dict.fromkeys([*item["cites"], *inline]))
            sentences.append(AnswerSentence(text=text, cites=cites))
        return sentences


class GeminiAnswerChecker(AnswerChecker):
    def __init__(self, settings: Settings, call: _GeminiCall | None = None) -> None:
        self._call = call or _GeminiCall(settings)
        self._model = settings.gemini_checker_model

    def check(self, sentences: list[AnswerSentence], sources: dict[str, SourcePassage]) -> list[CheckResult]:
        blocks = []
        for index, sentence in enumerate(sentences):
            cited = "\n".join(f"[{cite}] {sources[cite].text}" for cite in sentence.cites)
            blocks.append(f"SENTENCE {index}: {sentence.text}\nCITED PASSAGES:\n{cited}")
        data = self._call.json(self._model, _CHECKER_RULES, "\n\n".join(blocks), _CHECKER_SCHEMA)

        by_index = {item["index"]: CheckResult(Verdict(item["verdict"]), item.get("reason", "")) for item in data.get("verdicts", [])}
        # A sentence the checker did not rule on is NOT supported: silence is never approval.
        return [by_index.get(i, CheckResult(Verdict.NOT_SUPPORTED, "the checker gave no verdict")) for i in range(len(sentences))]
