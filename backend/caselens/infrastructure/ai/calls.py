"""One way to ask any AI provider for JSON: Gemini, Groq or DeepSeek. Every digest, question and check goes through `JsonModelCall.json`,
so the provider is chosen in one place (`make_ai_call`) and the prompts, checks and parsing stay the same for all of them.

The writers and checkers ask by ROLE ("writer" / "checker"); each provider turns the role into its own model name."""
from typing import Protocol

from caselens.domain.errors import AiCreditError, AiInvalidRequestError, AiKeyError, AiRateLimitError, AiUnavailableError
from caselens.infrastructure.config import Settings

WRITER = "writer"
CHECKER = "checker"
PROVIDERS = ("groq", "deepseek", "openrouter", "gemini")
PROVIDER_NAMES = {"groq": "Groq", "deepseek": "DeepSeek", "openrouter": "OpenRouter", "gemini": "Gemini"}


class JsonModelCall(Protocol):
    provider: str
    usage: dict

    def json(self, model: str, system: str, prompt: str, schema: dict, *, thinking_budget: int | None = None) -> dict: ...

    def model_for(self, role: str) -> str: ...


# What is wrong with each provider's key, if its last call was refused for the key itself: "credit" (no credit / allowance left) or
# "invalid". Cleared by the provider's next call that works, or when a new key is saved. Settings shows it.
_key_problems: dict[str, str] = {}


def note_key_problem(provider: str, kind: str) -> None:
    _key_problems[provider] = kind


def clear_key_problem(provider: str) -> None:
    _key_problems.pop(provider, None)


def key_problem(provider: str) -> str | None:
    return _key_problems.get(provider)


def forget_key_problem(provider: str | None = None) -> None:
    """A new key was saved (for one provider, or None for all): its old problem no longer applies."""
    if provider is None:
        _key_problems.clear()
    else:
        clear_key_problem(provider)


def api_key_for(settings: Settings, provider: str) -> str | None:
    return {"groq": settings.groq_api_key, "deepseek": settings.deepseek_api_key, "openrouter": settings.openrouter_api_key, "gemini": settings.gemini_api_key}[provider]


def ai_configured(settings: Settings) -> bool:
    """Is any provider's key set? (Without one, digests and questions say so instead of trying.)"""
    return any(api_key_for(settings, p) for p in PROVIDERS)


def provider_order(settings: Settings) -> list[str]:
    """The chosen provider first, then the others that have a key: when one cannot answer, the next one writes."""
    chosen = settings.ai_provider if settings.ai_provider in PROVIDERS else "gemini"
    return list(dict.fromkeys(p for p in [chosen, *PROVIDERS] if api_key_for(settings, p)))


def _single(settings: Settings, provider: str) -> JsonModelCall:
    if provider == "gemini":
        from caselens.infrastructure.ai.gemini_answerer import _GeminiCall

        return _GeminiCall(settings)
    from caselens.infrastructure.ai.openai_style_call import OpenAiStyleCall

    return OpenAiStyleCall.for_provider(settings, provider)


def make_ai_call(settings: Settings) -> JsonModelCall:
    """The call every writer and checker uses: the chosen provider, with the others that have a key behind it."""
    order = provider_order(settings)
    if not order:
        raise AiKeyError("No AI key is set.")
    if len(order) == 1:
        return _single(settings, order[0])
    return ChainedCall([_single(settings, p) for p in order])


def writer_model_name(settings: Settings) -> str:
    """The model that writes, as recorded on a digest ("which AI wrote this")."""
    order = provider_order(settings)
    if not order:
        return settings.gemini_writer_model
    return model_name(settings, order[0])


def model_name(settings: Settings, provider: str) -> str:
    """The model that writes for this provider."""
    return {"groq": settings.groq_model, "deepseek": settings.deepseek_model, "openrouter": settings.openrouter_model, "gemini": settings.gemini_writer_model}[provider]


class ChainedCall:
    """Providers in order. One that is busy, down or out of allowance hands the SAME request to the next; a key that is refused
    is noted for Settings and the next provider is tried too (a refused key costs no tokens). A request the provider refused as such
    (`AiInvalidRequestError`) stops here: the next provider would only repeat it. Only when all fail does the caller see an error
    (the first one that says what to do: a key / credit problem before "busy")."""

    def __init__(self, calls: list[JsonModelCall]) -> None:
        self._calls = calls
        self.provider = calls[0].provider

    @property
    def usage(self) -> dict:
        total = {"calls": 0, "input_tokens": 0, "output_tokens": 0}
        for call in self._calls:
            for key in total:
                total[key] += call.usage.get(key, 0)
        return total

    def model_for(self, role: str) -> str:
        return self._calls[0].model_for(role)

    def json(self, model: str, system: str, prompt: str, schema: dict, *, thinking_budget: int | None = None) -> dict:
        failures: list[AiUnavailableError] = []
        for call in self._calls:
            try:
                return call.json(model, system, prompt, schema, thinking_budget=thinking_budget)
            except AiInvalidRequestError:
                raise  # the request itself was refused: another provider would be sent the same request (and more tokens) for nothing
            except AiUnavailableError as exc:  # key, credit, rate limit, busy, timeout: the next provider has its own key and limits
                failures.append(exc)
        for kind in (AiKeyError, AiCreditError, AiRateLimitError):  # the most useful message for the student
            for exc in failures:
                if isinstance(exc, kind) and type(exc) is kind:
                    raise exc
        raise failures[-1]
