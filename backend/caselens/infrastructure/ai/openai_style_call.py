"""Groq and DeepSeek: both speak the OpenAI-style chat API. Groq through its own SDK (`groq`), DeepSeek through the `openai` SDK at
DeepSeek's address (DeepSeek's documented way). Same `json(...)` as the Gemini call, so every writer and checker works unchanged.

Groq's gpt-oss and Qwen models follow a JSON schema exactly ("strict" structured outputs). DeepSeek only promises valid JSON, so the
schema is put in the prompt and the answer is checked against it here; a wrong or empty answer is asked again."""
import copy
import json
import logging
import time
from collections.abc import Callable

import jsonschema

from caselens.domain.errors import AiCreditError, AiInvalidRequestError, AiKeyError, AiRateLimitError, AiUnavailableError
from caselens.infrastructure.ai.calls import CHECKER, PROVIDER_NAMES, REPAIR, WRITER, clear_key_problem, note_key_problem
from caselens.infrastructure.ai.models import openrouter_model
from caselens.infrastructure.config import Settings

logger = logging.getLogger(__name__)

_DEEPSEEK_URL = "https://api.deepseek.com"
_OPENROUTER_URL = "https://openrouter.ai/api/v1"
_OPENROUTER_HEADERS = {"X-Title": "CaseLens"}  # how OpenRouter names the app on the key owner's activity page
_MAX_OUTPUT_TOKENS = 32_000  # a long digest plus its reasoning; well under each model's limit


def _read_json(text: str) -> dict:
    """The JSON object in an answer. A model without JSON mode may wrap it in ```json fences or add a line around it."""
    try:
        return json.loads(text)
    except ValueError:
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            raise
        return json.loads(text[start : end + 1])


def _per_day(detail: str) -> bool:
    """A 429 for a daily allowance ("free-models-per-day"), not a per-minute one."""
    text = detail.lower()
    return "per-day" in text or "per day" in text or "perday" in text


def _too_long(detail: str) -> bool:
    """The case is longer than this model's context: another provider may take it."""
    text = detail.lower()
    return "context length" in text or "context_length" in text or "maximum context" in text or "too many tokens" in text


def strict_schema(schema: dict) -> dict:
    """A schema in the shape strict mode needs: every object closed (`additionalProperties: false`) and every property listed in
    `required`; a property that was optional may be null instead. Gemini's `"nullable": true` becomes a `null` type."""
    out = copy.deepcopy(schema)

    def walk(node: dict, optional: bool = False) -> None:
        if node.pop("nullable", False) or optional:
            kind = node.get("type")
            if isinstance(kind, str):
                node["type"] = [kind, "null"]
        if node.get("type") == "object" or (isinstance(node.get("type"), list) and "object" in node["type"]):
            properties = node.setdefault("properties", {})
            was_required = set(node.get("required", []))
            for name, child in properties.items():
                walk(child, optional=name not in was_required)
            node["required"] = list(properties)
            node["additionalProperties"] = False
        if isinstance(node.get("items"), dict):
            walk(node["items"])

    walk(out)
    return out


def standard_schema(schema: dict) -> dict:
    """The same schema in plain JSON Schema (Gemini's `"nullable": true` becomes a `null` type), for providers that only read
    the schema from the prompt and for checking their answer."""
    out = copy.deepcopy(schema)

    def walk(node: dict) -> None:
        if node.pop("nullable", False) and isinstance(node.get("type"), str):
            node["type"] = [node["type"], "null"]
        for child in node.get("properties", {}).values():
            walk(child)
        if isinstance(node.get("items"), dict):
            walk(node["items"])

    walk(out)
    return out


class OpenAiStyleCall:
    """One provider (Groq or DeepSeek) with retries; errors become the app's own (key, credit, rate limit, busy)."""

    def __init__(self, client, provider: str, models: dict[str, str], *, strict: bool, reasoning_effort: str | None = None,
                 max_retries: int = 3, sleep: Callable[[float], None] = time.sleep, extra_body: dict | None = None,
                 json_mode: bool = True) -> None:
        self._client = client
        self.provider = provider
        self._models = models
        self._strict = strict
        self._reasoning_effort = reasoning_effort
        self._extra_body = extra_body  # provider-only fields the SDK does not know (OpenRouter's `reasoning`)
        self._json_mode = json_mode  # False: the model does not take `response_format`; the shape is in the instructions only
        self._max_retries = max_retries
        self._sleep = sleep
        self.usage = {"calls": 0, "input_tokens": 0, "output_tokens": 0}

    @classmethod
    def for_provider(cls, settings: Settings, provider: str) -> "OpenAiStyleCall":
        if provider == "groq":
            from groq import Groq

            client = Groq(api_key=settings.groq_api_key, timeout=settings.ai_timeout_seconds, max_retries=0)
            models = {WRITER: settings.groq_model, CHECKER: settings.groq_checker_model, REPAIR: settings.groq_model}
            return cls(client, "groq", models, strict=True, reasoning_effort=settings.groq_reasoning_effort, max_retries=settings.gemini_max_retries)
        if provider == "deepseek":
            from openai import OpenAI

            client = OpenAI(api_key=settings.deepseek_api_key, base_url=_DEEPSEEK_URL, timeout=settings.ai_timeout_seconds, max_retries=0)
            models = {WRITER: settings.deepseek_model, CHECKER: settings.deepseek_checker_model, REPAIR: settings.deepseek_model}
            return cls(client, "deepseek", models, strict=False, max_retries=settings.gemini_max_retries)
        if provider == "openrouter":
            from openai import OpenAI

            client = OpenAI(
                api_key=settings.openrouter_api_key, base_url=_OPENROUTER_URL, timeout=settings.ai_timeout_seconds, max_retries=0,
                default_headers=_OPENROUTER_HEADERS,
            )
            models = {WRITER: settings.openrouter_model, CHECKER: settings.openrouter_checker_model, REPAIR: settings.openrouter_model}
            # The schema goes in the prompt and the answer is checked here (as for DeepSeek direct): OpenRouter can route a model to
            # hosts that do not all enforce a strict schema. The model thinks first (`reasoning`), then answers with the JSON only.
            # The writer thinks at the set effort ("low" by default: it was about a fifth of a digest's output); the checker and the
            # repair do not think at all (see `_request`).
            extra = {"reasoning": {"effort": settings.openrouter_reasoning_effort}} if settings.openrouter_reasoning else None
            known = openrouter_model(settings.openrouter_model)
            json_mode = settings.openrouter_json_mode if settings.openrouter_json_mode is not None else (known.json_mode if known else True)
            return cls(client, "openrouter", models, strict=False, max_retries=settings.gemini_max_retries, extra_body=extra, json_mode=json_mode)
        raise ValueError(f"Not an OpenAI-style provider: {provider}")

    def model_for(self, role: str) -> str:
        if role == REPAIR and REPAIR not in self._models:
            role = WRITER  # the repair rewrites with the writer's model
        return self._models.get(role, role)  # a real model name (an older caller, an eval script) is used as given

    def _request(self, model: str, system: str, prompt: str, schema: dict, think: bool = True) -> dict:
        """`think`: let the model reason before answering. Only the writer does: for the checker and the repair, reasoning took most of
        a digest's time and output cost (about 74% of all output tokens on a real case) for a yes/no or a one-sentence answer."""
        # OpenRouter reads `max_tokens`; Groq and DeepSeek read the newer `max_completion_tokens`.
        limit = "max_tokens" if self.provider == "openrouter" else "max_completion_tokens"
        request: dict = {"model": model, "temperature": 0, limit: _MAX_OUTPUT_TOKENS}
        if self._extra_body:
            request["extra_body"] = self._extra_body if think else {**self._extra_body, "reasoning": {"enabled": False}}
        if self._strict:
            request["response_format"] = {"type": "json_schema", "json_schema": {"name": "answer", "strict": True, "schema": strict_schema(schema)}}
            request["messages"] = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
            if self._reasoning_effort:
                request["reasoning_effort"] = self._reasoning_effort if think else "low"  # gpt-oss cannot turn it off: the least
            # Groq: the answer only, no thinking text. gpt-oss models take `include_reasoning`; the others `reasoning_format`.
            if model.startswith("openai/gpt-oss"):
                request["include_reasoning"] = False
            else:
                request["reasoning_format"] = "hidden"
        else:
            shape = json.dumps(standard_schema(schema), ensure_ascii=False, separators=(",", ":"))
            if self._json_mode:
                request["response_format"] = {"type": "json_object"}
            request["messages"] = [
                {"role": "system", "content": f"{system}\n\nAnswer with one JSON object only, matching this JSON schema exactly:\n{shape}"},
                {"role": "user", "content": prompt},
            ]
        return request

    def json(self, model: str, system: str, prompt: str, schema: dict, *, thinking_budget: int | None = None) -> dict:
        name = PROVIDER_NAMES[self.provider]
        think = model not in (CHECKER, REPAIR) and thinking_budget != 0  # a role, or (older callers) a model name: those think
        model = self.model_for(model)
        request = self._request(model, system, prompt, schema, think)
        last_problem = "no attempt made"
        rate_limited = False
        for attempt in range(self._max_retries + 1):
            try:
                started = time.monotonic()
                response = self._client.chat.completions.create(**request)
                self._count(response, model, time.monotonic() - started)
                text = (response.choices[0].message.content or "").strip()
                if not text:
                    raise ValueError("empty answer")
                data = _read_json(text)
                if not self._strict:
                    jsonschema.validate(data, standard_schema(schema))  # DeepSeek only promises JSON, not the shape
                clear_key_problem(self.provider)
                return data
            except (ValueError, jsonschema.ValidationError) as exc:  # json.JSONDecodeError is a ValueError
                last_problem = f"unusable answer ({str(exc)[:80]})"
            except Exception as exc:  # the SDKs' own errors: sorted by HTTP status
                status = getattr(exc, "status_code", None)
                detail = str(getattr(exc, "message", "") or exc)
                if status == 401 or (status == 403 and "permission" not in detail.lower()) or "invalid api key" in detail.lower():
                    note_key_problem(self.provider, "invalid")
                    raise AiKeyError(f"{name} refused the key ({status}): {detail[:200]}") from exc
                if status == 402 or "insufficient balance" in detail.lower():
                    note_key_problem(self.provider, "credit")
                    raise AiCreditError(f"{name} refused the request ({status}): no credit left") from exc
                if status == 413 or (status == 429 and "request too large" in detail.lower()) or _too_long(detail):
                    # A free plan's tokens-per-minute is smaller than one case: waiting cannot help, a paid plan does.
                    raise AiRateLimitError(f"{name}: the case is larger than this key's per-minute limit ({detail[:160]})") from exc
                if status == 429 and _per_day(detail):
                    # A free plan's requests for today are used up (OpenRouter's free models): waiting a minute cannot help.
                    note_key_problem(self.provider, "credit")
                    raise AiCreditError(f"{name} refused the request ({status}): today's free requests are used up") from exc
                if status == 429:
                    rate_limited, last_problem = True, "rate limited"
                    if attempt < self._max_retries:
                        self._sleep(10 * (attempt + 1))
                    continue
                if status is not None and 400 <= status < 500:  # the request itself was refused: not retried here or elsewhere
                    raise AiInvalidRequestError(f"{name} refused the request ({status}): {detail[:200]}") from exc
                last_problem = f"server error {status}" if status else f"no connection ({type(exc).__name__})"
            if attempt < self._max_retries:
                self._sleep(5 * 2**attempt)
        logger.warning("%s %s did not answer (%s)", self.provider, model, last_problem)
        if rate_limited and last_problem == "rate limited":
            raise AiRateLimitError(f"{name} {model} failed ({last_problem}).")
        raise AiUnavailableError(f"{name} {model} failed after {self._max_retries + 1} attempts ({last_problem}).")

    def _count(self, response, model: str, seconds: float) -> None:
        usage = getattr(response, "usage", None)
        tokens_in = getattr(usage, "prompt_tokens", 0) or 0
        tokens_out = getattr(usage, "completion_tokens", 0) or 0
        details = getattr(usage, "completion_tokens_details", None)
        thinking = getattr(details, "reasoning_tokens", 0) or 0
        self.usage["calls"] += 1
        self.usage["input_tokens"] += tokens_in
        self.usage["output_tokens"] += tokens_out
        logger.info("%s %s: %.1fs, %s in, %s out (%s of it thinking)", self.provider, model, seconds, tokens_in, tokens_out, thinking)


def check_key(provider: str, key: str, timeout_seconds: float = 15.0) -> bool | None:
    """Is this a working key? Lists the provider's models (free). True works, False refused, None: could not tell (offline)."""
    try:
        if provider == "groq":
            from groq import Groq

            client = Groq(api_key=key, timeout=timeout_seconds, max_retries=0)
        else:
            from openai import OpenAI

            if provider == "openrouter":
                # OpenRouter lists its models to anyone, so that says nothing about the key: ask about the key itself.
                import httpx

                answer = httpx.get(f"{_OPENROUTER_URL}/key", headers={"Authorization": f"Bearer {key}"}, timeout=timeout_seconds)
                if answer.status_code in (401, 403):
                    return False
                return True if answer.status_code == 200 else None
            client = OpenAI(api_key=key, base_url=_DEEPSEEK_URL, timeout=timeout_seconds, max_retries=0)
        client.models.list()
        return True
    except Exception as exc:  # noqa: BLE001
        status = getattr(exc, "status_code", None)
        return False if status in (400, 401, 403) else None
