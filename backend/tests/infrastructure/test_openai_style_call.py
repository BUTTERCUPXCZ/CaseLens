"""Groq and DeepSeek behind the same `json(...)` as Gemini: the request each provider needs, the answer read and checked, every
refusal turned into the app's own error, and the next provider taking over when one cannot answer. No network: fake clients."""
import json
from types import SimpleNamespace

import pytest

from caselens.domain.errors import AiCreditError, AiKeyError, AiRateLimitError, AiUnavailableError
from caselens.infrastructure.ai import calls
from caselens.infrastructure.ai.calls import CHECKER, WRITER, ChainedCall
from caselens.infrastructure.ai.openai_style_call import OpenAiStyleCall, strict_schema

SCHEMA = {
    "type": "object",
    "properties": {
        "verdicts": {"type": "array", "items": {"type": "object", "properties": {"index": {"type": "integer"}, "reason": {"type": "string"}}, "required": ["index"]}},
        "heading": {"type": "string", "nullable": True},
    },
    "required": ["verdicts"],
}
GOOD = {"verdicts": [{"index": 0, "reason": "said in P6"}], "heading": None}


class _ApiError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status_code, self.message = status, message


class _Client:
    """Answers with the scripted replies in turn: a dict (as JSON), a string (raw text), or an exception."""

    def __init__(self, *replies):
        self.replies, self.requests = list(replies), []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **request):
        self.requests.append(request)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        text = json.dumps(reply) if isinstance(reply, dict) else reply
        usage = SimpleNamespace(prompt_tokens=100, completion_tokens=40, completion_tokens_details=SimpleNamespace(reasoning_tokens=10))
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))], usage=usage)


def _groq(*replies):
    return OpenAiStyleCall(_Client(*replies), "groq", {WRITER: "openai/gpt-oss-120b", CHECKER: "openai/gpt-oss-20b"}, strict=True, reasoning_effort="medium", max_retries=2, sleep=lambda _: None)


def _deepseek(*replies):
    return OpenAiStyleCall(_Client(*replies), "deepseek", {WRITER: "deepseek-flash", CHECKER: "deepseek-flash"}, strict=False, max_retries=2, sleep=lambda _: None)


@pytest.fixture(autouse=True)
def _no_key_problem_left_behind():
    yield
    calls.forget_key_problem()


def test_strict_schema_closes_every_object_and_lists_every_field():
    strict = strict_schema(SCHEMA)
    assert strict["additionalProperties"] is False and strict["required"] == ["verdicts", "heading"]
    assert strict["properties"]["heading"]["type"] == ["string", "null"] and "nullable" not in strict["properties"]["heading"]
    item = strict["properties"]["verdicts"]["items"]
    assert item["additionalProperties"] is False and item["required"] == ["index", "reason"]
    assert item["properties"]["reason"]["type"] == ["string", "null"]  # was optional: may be null now
    assert "additionalProperties" not in SCHEMA  # the original is untouched


def test_groq_is_asked_for_the_exact_schema_with_the_role_s_model_and_no_thinking_text():
    call = _groq(GOOD)
    assert call.json(CHECKER, "Judge.", "Sentences", SCHEMA) == GOOD
    request = call._client.requests[0]
    assert request["model"] == "openai/gpt-oss-20b" and request["temperature"] == 0
    assert request["response_format"]["type"] == "json_schema" and request["response_format"]["json_schema"]["strict"] is True
    assert request["include_reasoning"] is False and request["reasoning_effort"] == "medium" and "reasoning_format" not in request
    assert call.usage == {"calls": 1, "input_tokens": 100, "output_tokens": 40}


def test_deepseek_gets_the_schema_in_the_prompt_and_a_wrong_answer_is_asked_again():
    call = _deepseek("", {"verdicts": "not a list"}, GOOD)  # empty, then the wrong shape, then right
    assert call.json(WRITER, "Write.", "Text", SCHEMA) == GOOD
    first = call._client.requests[0]
    assert first["response_format"] == {"type": "json_object"} and '"verdicts"' in first["messages"][0]["content"]
    assert len(call._client.requests) == 3


@pytest.mark.parametrize(
    ("error", "expected", "problem"),
    [
        (_ApiError(401, "Invalid API Key"), AiKeyError, "invalid"),
        (_ApiError(402, "Insufficient Balance"), AiCreditError, "credit"),
        (_ApiError(413, "Request too large for model on tokens per minute (TPM): Limit 8000"), AiRateLimitError, None),
    ],
)
def test_a_refusal_that_waiting_cannot_fix_is_said_at_once(error, expected, problem):
    call = _groq(error)
    with pytest.raises(expected):
        call.json(WRITER, "s", "p", SCHEMA)
    assert len(call._client.requests) == 1 and calls.key_problem("groq") == problem


def test_busy_or_too_many_is_tried_again_then_reported():
    assert _groq(_ApiError(503, "over capacity"), GOOD).json(WRITER, "s", "p", SCHEMA) == GOOD
    with pytest.raises(AiRateLimitError):
        _groq(*[_ApiError(429, "rate limit")] * 3).json(WRITER, "s", "p", SCHEMA)
    with pytest.raises(AiUnavailableError):
        _groq(*[_ApiError(500, "server")] * 3).json(WRITER, "s", "p", SCHEMA)


def test_when_the_chosen_provider_cannot_answer_the_next_one_writes():
    groq, deepseek = _groq(*[_ApiError(503, "over capacity")] * 3), _deepseek(GOOD)
    chain = ChainedCall([groq, deepseek])
    assert chain.json(WRITER, "s", "p", SCHEMA) == GOOD
    assert chain.usage["calls"] == 1  # only answers are counted


def test_when_every_provider_fails_the_most_useful_reason_is_given():
    chain = ChainedCall([_groq(_ApiError(401, "Invalid API Key")), _deepseek(*[_ApiError(503, "busy")] * 3)])
    with pytest.raises(AiKeyError):  # "your key is not valid" says what to do; "busy" would not
        chain.json(WRITER, "s", "p", SCHEMA)


def test_the_chosen_provider_comes_first_and_only_providers_with_a_key_are_used():
    from caselens.infrastructure.config import Settings

    settings = Settings(_env_file=None, ai_provider="deepseek", groq_api_key="g", deepseek_api_key="d", gemini_api_key=None)
    assert calls.provider_order(settings) == ["deepseek", "groq"]
    assert calls.writer_model_name(settings) == "deepseek-flash"
    assert calls.ai_configured(Settings(_env_file=None, gemini_api_key=None, groq_api_key=None, deepseek_api_key=None)) is False


def test_a_request_the_provider_refuses_as_such_is_not_retried_and_not_sent_to_the_next_provider():
    """A 400 that is not about the key, credit or rate would be refused again anywhere: asking more only spends more."""
    from caselens.domain.errors import AiInvalidRequestError

    groq, deepseek = _groq(_ApiError(400, "response_format: invalid schema")), _deepseek(GOOD)
    with pytest.raises(AiInvalidRequestError):
        ChainedCall([groq, deepseek]).json(WRITER, "s", "p", SCHEMA)
    assert len(groq._client.requests) == 1 and deepseek._client.requests == []


def test_a_case_longer_than_the_models_context_goes_to_the_next_provider():
    groq, deepseek = _groq(_ApiError(400, "Please reduce the length of the messages: context_length_exceeded")), _deepseek(GOOD)
    assert ChainedCall([groq, deepseek]).json(WRITER, "s", "p", SCHEMA) == GOOD
    assert len(groq._client.requests) == 1  # not retried on the same model


@pytest.mark.parametrize(
    ("error", "kind"),
    [
        (_ApiError(401, "Invalid API Key"), AiKeyError),
        (_ApiError(402, "Insufficient Balance"), AiCreditError),
        (_ApiError(429, "rate limit"), AiRateLimitError),
        (_ApiError(503, "over capacity"), AiUnavailableError),
    ],
)
def test_key_credit_rate_and_busy_refusals_hand_over_to_the_next_provider(error, kind):
    with pytest.raises(kind):  # alone, the provider says what went wrong ...
        _groq(*[error] * 3).json(WRITER, "s", "p", SCHEMA)
    assert ChainedCall([_groq(*[error] * 3), _deepseek(GOOD)]).json(WRITER, "s", "p", SCHEMA) == GOOD  # ... behind it, the next one writes


def _openrouter(*replies):
    return OpenAiStyleCall(
        _Client(*replies), "openrouter", {WRITER: "deepseek/deepseek-v4.1-flash", CHECKER: "deepseek/deepseek-v4.1-flash"}, strict=False,
        max_retries=2, sleep=lambda _: None, extra_body={"reasoning": {"enabled": True}},
    )


def test_openrouter_gets_the_schema_in_the_prompt_and_max_tokens_and_a_wrong_answer_is_asked_again():
    call = _openrouter({"something": "else"}, GOOD)
    assert call.json(WRITER, "rules", "the case", SCHEMA) == GOOD
    request = call._client.requests[0]
    assert request["model"] == "deepseek/deepseek-v4.1-flash" and request["response_format"] == {"type": "json_object"}
    assert request["extra_body"] == {"reasoning": {"enabled": True}}  # OpenRouter's own field: the model thinks before answering
    assert "max_tokens" in request and "max_completion_tokens" not in request  # the field OpenRouter reads
    assert "JSON schema" in request["messages"][0]["content"] and len(call._client.requests) == 2


def test_openrouter_s_free_requests_for_today_used_up_says_so_at_once():
    call = _openrouter(_ApiError(429, "Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day"))
    with pytest.raises(AiCreditError):
        call.json(WRITER, "s", "p", SCHEMA)
    assert len(call._client.requests) == 1 and calls.key_problem("openrouter") == "credit"


def test_openrouter_is_built_with_its_address_and_counts_as_a_provider():
    from caselens.infrastructure.config import Settings

    settings = Settings(openrouter_api_key="sk-or-test", ai_provider="openrouter", groq_api_key=None, deepseek_api_key=None, gemini_api_key=None)
    call = OpenAiStyleCall.for_provider(settings, "openrouter")
    assert call.provider == "openrouter" and str(call._client.base_url).startswith("https://openrouter.ai/api/v1")
    assert calls.provider_order(settings) == ["openrouter"] and calls.writer_model_name(settings) == "deepseek/deepseek-v4.1-flash"
    assert call._extra_body == {"reasoning": {"enabled": True}}
