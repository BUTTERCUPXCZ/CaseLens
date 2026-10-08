"""The website's Settings page: which AI writes the digests, and picking the OpenRouter model. The key itself is never sent."""
import pytest
from fastapi.testclient import TestClient

from caselens.composition import Services
from caselens.infrastructure.config import Settings
from caselens.main import create_app
from caselens.presentation.api import ai_info
from caselens.presentation.dependencies import get_session

NEMOTRON = "nvidia/nemotron-3-ultra-550b-a55b:free"
DEEPSEEK = "deepseek/deepseek-v4.1-flash"


def settings(**changes):
    base = dict(_env_file=None, database_url="sqlite:///x.db", ai_provider="openrouter", openrouter_api_key="sk-or-secret", ai_only_chosen=True)
    return Settings(**{**base, **changes})


@pytest.fixture
def site(monkeypatch, db_session):
    def use(**changes):
        monkeypatch.setattr(ai_info, "get_settings", lambda: settings(**changes))
        app = create_app()
        app.dependency_overrides[get_session] = lambda: db_session
        return TestClient(app)
    return use


def test_the_site_says_which_ai_writes_and_never_the_key(site):
    response = site(openrouter_model=NEMOTRON).get("/ai-info")
    body = response.json()
    assert (body["provider"], body["model"], body["free"], body["only_chosen"], body["ready"]) == ("OpenRouter", "Nemotron 3 Ultra (free, for testing)", True, True, True)
    assert [m["id"] for m in body["models"]] == [DEEPSEEK, NEMOTRON]  # what can be picked
    assert "sk-or" not in response.text


def test_without_a_key_the_site_says_it_is_not_ready(site):
    body = site(openrouter_api_key=None).get("/ai-info").json()
    assert body["ready"] is False and body["model"] == "DeepSeek V4.1 Flash" and body["free"] is False


def test_a_model_picked_on_the_site_writes_the_next_digests(site, db_session):
    client = site(openrouter_model=DEEPSEEK)
    picked = client.put("/ai-model", json={"model": NEMOTRON})
    assert picked.status_code == 200 and picked.json()["model_id"] == NEMOTRON
    assert client.get("/ai-info").json()["model_id"] == NEMOTRON  # remembered
    used = Services(db_session)._settings  # what a request or a job builds its AI from
    assert used.openrouter_model == NEMOTRON and used.openrouter_checker_model == NEMOTRON


def test_only_a_listed_model_can_be_picked(site):
    assert site().put("/ai-model", json={"model": "anthropic/some-expensive-model"}).status_code == 422


def test_the_model_cannot_be_picked_when_the_site_does_not_use_openrouter(site):
    client = site(ai_provider="gemini", gemini_api_key="k")
    assert client.get("/ai-info").json()["models"] == []
    assert client.put("/ai-model", json={"model": NEMOTRON}).status_code == 409
