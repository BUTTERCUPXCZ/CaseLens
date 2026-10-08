"""The website's Settings page reads which AI writes the digests; the key itself is never sent."""
from fastapi.testclient import TestClient

from caselens.infrastructure.config import Settings
from caselens.main import create_app
from caselens.presentation.api import ai_info


def test_the_site_says_which_ai_writes_and_never_the_key(monkeypatch):
    settings = Settings(_env_file=None, database_url="sqlite:///x.db", ai_provider="openrouter", openrouter_api_key="sk-or-secret",
                        openrouter_model="nvidia/nemotron-3-ultra-550b-a55b:free", ai_only_chosen=True)
    monkeypatch.setattr(ai_info, "get_settings", lambda: settings)
    response = TestClient(create_app()).get("/ai-info")
    assert response.json() == {"provider": "OpenRouter", "model": "Nemotron 3 Ultra (free, for testing)", "free": True, "only_chosen": True, "ready": True}
    assert "sk-or" not in response.text


def test_without_a_key_the_site_says_it_is_not_ready(monkeypatch):
    settings = Settings(_env_file=None, database_url="sqlite:///x.db", ai_provider="openrouter", openrouter_api_key=None, gemini_api_key=None)
    monkeypatch.setattr(ai_info, "get_settings", lambda: settings)
    body = TestClient(create_app()).get("/ai-info").json()
    assert body["ready"] is False and body["model"] == "DeepSeek V4.1 Flash" and body["free"] is False
