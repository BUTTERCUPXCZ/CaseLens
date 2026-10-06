"""How a refused Gemini call is reported: no credit left is its own error (asking again cannot help); a rate limit is retried."""
import pytest
from google.genai import errors as genai_errors

from caselens.domain.errors import AiCreditError, AiUnavailableError
from caselens.infrastructure.ai.gemini_answerer import _GeminiCall
from caselens.infrastructure.config import Settings


class _Models:
    def __init__(self, code):
        self.code, self.calls = code, 0

    def generate_content(self, **_):
        self.calls += 1
        raise genai_errors.ClientError(self.code, {"error": {"code": self.code, "message": "Your prepayment credits are depleted.", "status": "x"}})


def call_with(code):
    call = _GeminiCall(Settings(gemini_api_key="test-key", gemini_max_retries=2), sleep=lambda _: None)
    call._client = type("Client", (), {"models": _Models(code)})()
    return call


def test_no_credit_left_is_its_own_error_and_is_not_retried():
    call = call_with(402)
    with pytest.raises(AiCreditError, match="402"):
        call.json("m", "s", "p", {})
    assert call._client.models.calls == 1


def test_a_rate_limit_is_retried_before_giving_up():
    call = call_with(429)
    with pytest.raises(AiUnavailableError) as raised:
        call.json("m", "s", "p", {})
    assert not isinstance(raised.value, AiCreditError) and call._client.models.calls == 3
