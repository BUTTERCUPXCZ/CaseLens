"""How a refused Gemini call is reported: no credit left is its own error (asking again cannot help); a rate limit is retried."""
import pytest
from google.genai import errors as genai_errors

from caselens.domain.errors import AiCreditError, AiUnavailableError
from caselens.infrastructure.ai.gemini_answerer import _GeminiCall
from caselens.infrastructure.config import Settings


@pytest.fixture(autouse=True)
def _no_credit_problem_left_behind():
    from caselens.infrastructure.ai import gemini_answerer

    yield
    gemini_answerer.forget_credit_problem()


class _Models:
    def __init__(self, code):
        self.code, self.calls = code, 0

    def generate_content(self, **_):
        self.calls += 1
        raise genai_errors.ClientError(self.code, {"error": {"code": self.code, "message": "Your prepayment credits are depleted.", "status": "x"}})


def call_with(code):
    call = _GeminiCall(Settings(gemini_api_key="test-key", gemini_max_retries=2, gemini_fallback_models=[]), sleep=lambda _: None)
    call._client = type("Client", (), {"models": _Models(code)})()
    return call


def test_no_credit_left_is_its_own_error_and_is_not_retried():
    call = call_with(402)
    with pytest.raises(AiCreditError, match="402"):
        call.json("m", "s", "p", {})
    assert call._client.models.calls == 1


def test_a_rate_limit_is_retried_before_giving_up_and_then_says_it_is_the_keys_limit():
    from caselens.domain.errors import AiRateLimitError

    call = call_with(429)
    with pytest.raises(AiRateLimitError):
        call.json("m", "s", "p", {})
    assert call._client.models.calls == 3
    assert "few requests per minute" in AiRateLimitError.STUDENT_MESSAGE


class _QuotaModels:
    """Gemini's 429 for a free-tier key whose daily allowance is gone (the shape Google sends)."""

    def __init__(self, quota_id, value="20"):
        self.calls, self.quota_id, self.value = 0, quota_id, value

    def generate_content(self, **_):
        self.calls += 1
        raise genai_errors.ClientError(429, {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED", "message": "You exceeded your current quota, please check your plan and billing details.", "details": [{"@type": "type.googleapis.com/google.rpc.QuotaFailure", "violations": [{"quotaId": self.quota_id, "quotaValue": self.value}]}]}})


def _quota_call(quota_id, value="20"):
    call = _GeminiCall(Settings(gemini_api_key="test-key", gemini_max_retries=2, gemini_fallback_models=[]), sleep=lambda _: None)
    call._client = type("Client", (), {"models": _QuotaModels(quota_id, value)})()
    return call


def test_a_used_up_daily_allowance_says_so_at_once_instead_of_waiting():
    from caselens.infrastructure.ai import gemini_answerer

    call = _quota_call("GenerateRequestsPerDayPerProjectPerModel-FreeTier")
    with pytest.raises(AiCreditError, match="daily allowance"):
        call.json("m", "s", "p", {})
    assert call._client.models.calls == 1  # no minutes of pointless retries
    assert gemini_answerer.credit_problem_since() is not None  # Settings shows it
    gemini_answerer.forget_credit_problem()
    assert gemini_answerer.credit_problem_since() is None


def test_a_model_not_in_the_keys_plan_is_also_used_up():
    with pytest.raises(AiCreditError):
        _quota_call("GenerateRequestsPerMinutePerProjectPerModel-FreeTier", value="0").json("m", "s", "p", {})


def test_too_many_at_once_is_still_waited_out():
    call = _quota_call("GenerateRequestsPerMinutePerProjectPerModel")
    with pytest.raises(AiUnavailableError) as raised:
        call.json("m", "s", "p", {})
    assert not isinstance(raised.value, AiCreditError) and call._client.models.calls == 3


def test_the_student_reads_what_happened_and_what_to_do():
    message = AiCreditError.STUDENT_MESSAGE
    assert "run out of credit" in message and "Try again" in message and "Settings" in message


class _KeyModels:
    def __init__(self):
        self.calls = 0

    def generate_content(self, **_):
        self.calls += 1
        raise genai_errors.ClientError(400, {"error": {"code": 400, "status": "INVALID_ARGUMENT", "message": "API key not valid. Please pass a valid API key.", "details": [{"reason": "API_KEY_INVALID"}]}})


def test_a_key_google_refuses_says_so_and_is_not_retried():
    from caselens.domain.errors import AiKeyError
    from caselens.infrastructure.ai import gemini_answerer

    call = _GeminiCall(Settings(gemini_api_key="test-key", gemini_max_retries=2, gemini_fallback_models=[]), sleep=lambda _: None)
    call._client = type("Client", (), {"models": _KeyModels()})()
    with pytest.raises(AiKeyError):
        call.json("m", "s", "p", {})
    assert call._client.models.calls == 1 and gemini_answerer.key_problem() == "invalid"
    assert "not valid" in AiKeyError.STUDENT_MESSAGE and "Settings" in AiKeyError.STUDENT_MESSAGE


class _OverloadedModels:
    """Google's 503 "model is overloaded" for some models; the others answer."""

    def __init__(self, busy):
        self.busy, self.asked = set(busy), []

    def generate_content(self, model, **_):
        self.asked.append(model)
        if model in self.busy:
            raise genai_errors.ServerError(503, {"error": {"code": 503, "status": "UNAVAILABLE", "message": "This model is currently experiencing high demand."}})
        return type("Response", (), {"text": '{"ok": true}', "usage_metadata": None})()


def test_an_overloaded_model_hands_over_to_a_back_up_model():
    call = _GeminiCall(Settings(gemini_api_key="k", gemini_max_retries=1, gemini_fallback_models=["backup-a", "backup-b"]), sleep=lambda _: None)
    call._client = type("Client", (), {"models": _OverloadedModels({"main", "backup-a"})})()
    assert call.json("main", "s", "p", {}) == {"ok": True}
    assert call._client.models.asked == ["main", "main", "backup-a", "backup-a", "backup-b"]


def test_when_every_model_is_overloaded_the_digest_says_google_is_busy():
    call = _GeminiCall(Settings(gemini_api_key="k", gemini_max_retries=0, gemini_fallback_models=["backup-a"]), sleep=lambda _: None)
    call._client = type("Client", (), {"models": _OverloadedModels({"main", "backup-a"})})()
    with pytest.raises(AiUnavailableError, match="main, backup-a"):
        call.json("main", "s", "p", {})


class _AllowanceModels:
    """A free key: each model has its own daily allowance; `used_up` ones are gone for today."""

    def __init__(self, used_up):
        self.used_up, self.asked = set(used_up), []

    def generate_content(self, model, **_):
        self.asked.append(model)
        if model in self.used_up:
            raise genai_errors.ClientError(429, {"error": {"code": 429, "message": "You exceeded your current quota.", "details": [{"violations": [{"quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier", "quotaValue": "20"}]}]}})
        return type("Response", (), {"text": '{"ok": true}', "usage_metadata": None})()


def test_a_free_key_moves_on_to_a_model_with_allowance_left():
    call = _GeminiCall(Settings(gemini_api_key="k", gemini_max_retries=2, gemini_fallback_models=["backup-a", "backup-b"]), sleep=lambda _: None)
    call._client = type("Client", (), {"models": _AllowanceModels({"main", "backup-a"})})()
    assert call.json("main", "s", "p", {}) == {"ok": True}
    assert call._client.models.asked == ["main", "backup-a", "backup-b"]  # one try each: a used-up allowance is not retried


def test_when_every_models_allowance_is_gone_it_says_so():
    call = _GeminiCall(Settings(gemini_api_key="k", gemini_max_retries=2, gemini_fallback_models=["backup-a"]), sleep=lambda _: None)
    call._client = type("Client", (), {"models": _AllowanceModels({"main", "backup-a"})})()
    with pytest.raises(AiCreditError, match="main, backup-a"):
        call.json("main", "s", "p", {})


class _RefusingModels:
    def __init__(self, message):
        self.message, self.calls = message, 0

    def generate_content(self, **_):
        self.calls += 1
        raise genai_errors.ClientError(400, {"error": {"code": 400, "status": "INVALID_ARGUMENT", "message": self.message}})


def _refused(message):
    call = _GeminiCall(Settings(gemini_api_key="test-key", gemini_max_retries=2, gemini_fallback_models=["back-up"]), sleep=lambda _: None)
    call._client = type("Client", (), {"models": _RefusingModels(message)})()
    return call


def test_a_request_google_refuses_as_such_is_its_own_error_and_no_back_up_model_is_tried():
    from caselens.domain.errors import AiInvalidRequestError

    call = _refused("Invalid JSON payload received.")
    with pytest.raises(AiInvalidRequestError):
        call.json("m", "s", "p", {})
    assert call._client.models.calls == 1
    assert "not your file" in AiInvalidRequestError.STUDENT_MESSAGE


def test_a_case_too_long_for_the_model_may_go_to_another_provider():
    from caselens.domain.errors import AiRateLimitError

    call = _refused("The input token count (1200000) exceeds the maximum number of tokens allowed (1048576).")
    with pytest.raises(AiRateLimitError):
        call.json("m", "s", "p", {})
    assert call._client.models.calls == 1
