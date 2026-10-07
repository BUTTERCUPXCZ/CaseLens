"""Gemini adapters for `AnswerWriter` and `AnswerChecker`. This is the only module that imports the SDK."""
import json
import logging
import re
import threading
import time
from datetime import UTC, datetime
from collections.abc import Callable

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from caselens.application.ports.ai import AnswerChecker, AnswerRequest, AnswerWriter
from caselens.domain.digest import AnswerSentence, CheckResult, SourcePassage, Verdict
from caselens.domain.errors import AiCreditError, AiInvalidRequestError, AiKeyError, AiRateLimitError, AiUnavailableError
from caselens.infrastructure.ai.calls import CHECKER, REPAIR, WRITER, clear_key_problem, note_key_problem
from caselens.infrastructure.ai.calls import key_problem as calls_key_problem
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

_CHECKER_RULES = """You are a strict fact checker for a law-student tool. You get numbered passages, then numbered sentences, each
naming the passages it cites. Judge each sentence ONLY against its own cited passages, using no outside knowledge.
- supported: every claim in the sentence is stated in, or follows directly from, the cited passages.
- partly_supported: some claim is supported but another claim, number, name or conclusion is not.
- not_supported: the cited passages do not back the sentence, or it only sounds plausible.
Be strict: when unsure, do not say supported.
Also reject overstatement: a sentence is not supported if it says something more certain, more general or more
final than the passages do (for example, an allegation, a finding of probable cause or a party's argument written
as if the Court had decided it, or "always"/"all" where the passage says "in this case").
Answer in compact JSON: {"verdicts": [{"i": the sentence's number, "v": the verdict, "r": a short reason}]}. Give "r" ONLY for a verdict
that is not supported; leave it out for a supported sentence."""

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
                # i = the sentence's number, v = the verdict, r = why (only when not supported: a reason for every supported
                # sentence was most of the checker's answer and is never shown)
                "properties": {
                    "i": {"type": "integer"},
                    "v": {"type": "string", "enum": [v.value for v in Verdict]},
                    "r": {"type": "string"},
                },
                "required": ["i", "v"],
            },
        }
    },
    "required": ["verdicts"],
}


# Key problems are kept per provider in `calls` (Settings shows them); these names stay for older callers.
def _note_key_problem(kind: str) -> None:
    note_key_problem("gemini", kind)


def _clear_key_problem() -> None:
    clear_key_problem("gemini")


def key_problem() -> str | None:
    """ "credit", "invalid", or None while the Gemini key works."""
    return calls_key_problem("gemini")


def credit_problem_since() -> str | None:  # kept for older callers
    return key_problem() if key_problem() == "credit" else None


def forget_credit_problem() -> None:
    """A new key was saved: the old key's problem no longer applies."""
    _clear_key_problem()


def _key_refused(exc: genai_errors.ClientError) -> bool:
    """Google refused the key itself: not valid, expired, or no access (a 400 that says so, or 401 / 403)."""
    detail = f"{exc.details} {exc.message}"
    return exc.code in (401, 403) or (exc.code == 400 and ("API key not valid" in detail or "API_KEY_INVALID" in detail))


def _too_large(exc: genai_errors.ClientError) -> bool:
    detail = f"{exc.details} {exc.message}".lower()
    return exc.code == 413 or "token count" in detail or "too long" in detail or "exceeds the maximum" in detail


def _allowance_used_up(exc: genai_errors.ClientError) -> bool:
    """A 429 is usually "too many at once" (wait a minute). A per-day quota, or a quota of 0 (the model is not in the key's
    plan), is "used up": no waiting helps until billing is on or the next day."""
    detail = f"{exc.details} {exc.message}"
    return "PerDay" in detail or "quotaValue': '0'" in detail or '"quotaValue": "0"' in detail


_FALLBACK_ATTEMPTS = 2  # tries on each back-up model


class _GeminiCall:
    """One JSON-returning call with retries on rate limits and server errors."""

    def __init__(self, settings: Settings, sleep: Callable[[float], None] = time.sleep) -> None:
        if not settings.gemini_api_key:
            raise AiUnavailableError("GEMINI_API_KEY is not set.")
        timeout_ms = int(settings.gemini_timeout_seconds * 1000)
        self._client = genai.Client(api_key=settings.gemini_api_key, http_options=types.HttpOptions(timeout=timeout_ms))
        self._max_retries = settings.gemini_max_retries
        self._fallbacks = list(settings.gemini_fallback_models)
        self._models = {WRITER: settings.gemini_writer_model, CHECKER: settings.gemini_checker_model, REPAIR: settings.gemini_writer_model}
        self.provider = "gemini"
        self._sleep = sleep
        self.usage = {"calls": 0, "input_tokens": 0, "output_tokens": 0}  # for measuring what a digest costs
        self._usage_lock = threading.Lock()  # a digest's check groups run at the same time

    def model_for(self, role: str) -> str:
        if role == REPAIR and REPAIR not in self._models:
            role = WRITER  # the repair rewrites with the writer's model
        return self._models.get(role, role)  # a real model name (an older caller, an eval script) is used as given

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
        model = self.model_for(model)
        last_problem, tried, used_up = "no attempt made", [], 0
        # The asked model first; when Google keeps saying it is busy (503) or full (429 per minute), a back-up model of the same
        # family writes instead, so one overloaded model does not stop every digest.
        for current, attempts in [(model, self._max_retries + 1)] + [(m, _FALLBACK_ATTEMPTS) for m in self._fallbacks if m != model]:
            tried.append(current)
            for attempt in range(attempts):
                try:
                    started = time.monotonic()
                    response = self._client.models.generate_content(model=current, contents=prompt, config=config)
                    self._count(response, current, time.monotonic() - started)
                    _clear_key_problem()  # the key works (again)
                    return json.loads(response.text)
                except genai_errors.ClientError as exc:
                    if exc.code == 402:  # prepaid credit used up: retrying cannot help
                        _note_key_problem("credit")
                        raise AiCreditError(f"Gemini refused the request ({exc.code}): {exc.message}") from exc
                    if _key_refused(exc):
                        _note_key_problem("invalid")
                        raise AiKeyError(f"Gemini refused the key ({exc.code}): {exc.message}") from exc
                    if exc.code != 429 and _too_large(exc):  # another provider may take a longer case
                        raise AiRateLimitError(f"Gemini: the case is too long for {current} ({exc.code}): {exc.message}") from exc
                    if exc.code != 429:  # the request itself was refused: asking again, here or elsewhere, repeats the refusal
                        raise AiInvalidRequestError(f"Gemini refused the request ({exc.code}): {exc.message}") from exc
                    if _allowance_used_up(exc):  # this model's daily allowance (free tier) is gone: waiting cannot help,
                        last_problem, used_up = "daily allowance used up", used_up + 1  # but each model has its own allowance
                        break
                    last_problem = "rate limited"
                    if attempt < attempts - 1:
                        self._sleep(20 * (attempt + 1))  # per-minute quotas need a real pause, not 2 seconds
                    continue
                except genai_errors.ServerError as exc:
                    last_problem = f"server error {exc.code}"
                except (json.JSONDecodeError, TypeError) as exc:
                    last_problem = f"unreadable answer ({type(exc).__name__})"
                if attempt < attempts - 1:
                    self._sleep(5 * 2**attempt)  # 5, 10, 20 s: an overloaded model needs more than a few seconds
            logger.warning("gemini %s did not answer (%s)", current, last_problem)
        if used_up == len(tried):  # every model's allowance is gone: only billing (or tomorrow) helps
            _note_key_problem("credit")
            raise AiCreditError(f"Gemini refused the request (429): daily allowance used up on {', '.join(tried)}")
        if last_problem == "rate limited":  # the key's per-minute limit, on every model: it passes, but it is the key, not Google
            raise AiRateLimitError(f"Gemini failed on {', '.join(tried)} ({last_problem}).")
        raise AiUnavailableError(f"Gemini failed on {', '.join(tried)} ({last_problem}).")


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
        self._model = WRITER  # each provider picks its own writing model

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


def _pick(item: dict, short: str, long: str):
    """A field by its short name, or by the long name an older answer used."""
    return item[short] if short in item else item.get(long)


class GeminiAnswerChecker(AnswerChecker):
    def __init__(self, settings: Settings, call: _GeminiCall | None = None) -> None:
        self._call = call or _GeminiCall(settings)
        self._model = CHECKER

    def check(self, sentences: list[AnswerSentence], sources: dict[str, SourcePassage]) -> list[CheckResult]:
        # Each cited passage is written once, then each sentence names the ids it cites: a paragraph cited by ten sentences is not
        # sent ten times. The checker still judges each sentence only against its own cited passages.
        cited_ids = list(dict.fromkeys(cite for sentence in sentences for cite in sentence.cites))
        passages = "\n\n".join(f"[{cite}] {sources[cite].text}" for cite in cited_ids)
        claims = "\n\n".join(f"SENTENCE {index}: {sentence.text}\nCITES: {', '.join(sentence.cites)}" for index, sentence in enumerate(sentences))
        prompt = f"PASSAGES:\n{passages}\n\nSENTENCES (judge each only against the passages it cites):\n{claims}"
        data = self._call.json(self._model, _CHECKER_RULES, prompt, _CHECKER_SCHEMA)

        by_index = {
            _pick(item, "i", "index"): CheckResult(Verdict(_pick(item, "v", "verdict")), _pick(item, "r", "reason") or "")
            for item in data.get("verdicts", [])
        }
        # A sentence the checker did not rule on is NOT supported: silence is never approval.
        return [by_index.get(i, CheckResult(Verdict.NOT_SUPPORTED, "the checker gave no verdict")) for i in range(len(sentences))]


def check_gemini_key(key: str, timeout_seconds: float = 15.0) -> bool | None:
    """Is this a working Gemini key? Asks Google for its model list (free, uses no digest allowance). True: works. False: Google
    refuses the key. None: could not tell (offline, Google down), so the caller should not block on it."""
    client = genai.Client(api_key=key, http_options=types.HttpOptions(timeout=int(timeout_seconds * 1000)))
    try:
        next(iter(client.models.list(config={"page_size": 1})), None)
        return True
    except genai_errors.ClientError as exc:
        return False if _key_refused(exc) or exc.code == 400 else None
    except Exception:  # noqa: BLE001  network trouble: cannot tell
        return None
