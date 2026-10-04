"""The shared access code: closed without the cookie, open with it, /health always open, no gate when no code is set."""
import pytest
from fastapi.testclient import TestClient

from caselens.infrastructure.config import Settings
from caselens.main import create_app
from caselens.presentation import access_gate


@pytest.fixture(autouse=True)
def _reset_attempts():
    access_gate._wrong_attempts.clear()
    access_gate._all_wrong.clear()


def client_with_code(monkeypatch, code: str | None) -> TestClient:
    monkeypatch.setattr(access_gate, "get_settings", lambda: Settings(access_code=code))
    return TestClient(create_app())


def test_without_a_code_set_everything_is_open(monkeypatch):
    client = client_with_code(monkeypatch, None)
    assert client.get("/access").json() == {"required": False, "granted": True}
    assert client.get("/openapi.json").status_code == 200


def test_with_a_code_set_the_api_is_closed_until_the_code_is_entered(monkeypatch):
    client = client_with_code(monkeypatch, "pass-123")
    assert client.get("/openapi.json").status_code == 401
    assert client.get("/access").json() == {"required": True, "granted": False}
    assert client.post("/access", json={"code": "wrong"}).status_code == 401
    assert client.get("/openapi.json").status_code == 401

    assert client.post("/access", json={"code": " pass-123 "}).json() == {"required": True, "granted": True}
    assert client.get("/openapi.json").status_code == 200  # the cookie is kept by the client
    assert client.get("/access").json() == {"required": True, "granted": True}


def test_the_cookie_does_not_contain_the_code(monkeypatch):
    client = client_with_code(monkeypatch, "pass-123")
    response = client.post("/access", json={"code": "pass-123"})
    assert "pass-123" not in response.headers["set-cookie"]
    assert "HttpOnly" in response.headers["set-cookie"]


def test_too_many_wrong_codes_are_stopped(monkeypatch):
    client = client_with_code(monkeypatch, "pass-123")
    codes = [client.post("/access", json={"code": f"x{i}"}).status_code for i in range(12)]
    assert codes[:10] == [401] * 10
    assert codes[10:] == [429, 429]
    assert client.post("/access", json={"code": "pass-123"}).status_code == 429


def test_health_is_open_for_the_keep_awake_ping(monkeypatch):
    client = client_with_code(monkeypatch, "pass-123")
    assert client.get("/health").status_code != 401


def test_one_clients_wrong_tries_do_not_lock_out_another(monkeypatch):
    client = client_with_code(monkeypatch, "pass-123")
    for i in range(12):
        client.post("/access", json={"code": f"x{i}"}, headers={"x-forwarded-for": "1.1.1.1"})
    assert client.post("/access", json={"code": "x"}, headers={"x-forwarded-for": "1.1.1.1"}).status_code == 429
    other = client.post("/access", json={"code": "pass-123"}, headers={"x-forwarded-for": "2.2.2.2"})
    assert other.status_code == 200


def test_faking_a_new_address_each_time_does_not_give_unlimited_guesses(monkeypatch):
    client = client_with_code(monkeypatch, "pass-123")
    codes = [
        client.post("/access", json={"code": f"x{i}"}, headers={"x-forwarded-for": f"9.9.{i // 200}.{i % 200}"}).status_code
        for i in range(70)
    ]
    assert codes[:60] == [401] * 60
    assert set(codes[60:]) == {429}


def test_faked_addresses_cannot_fill_the_memory_of_remembered_clients(monkeypatch):
    client = client_with_code(monkeypatch, "pass-123")
    monkeypatch.setattr(access_gate, "_MAX_CLIENTS", 5)
    monkeypatch.setattr(access_gate, "_MAX_WRONG_PER_MINUTE_ALL", 1000)
    for i in range(30):
        client.post("/access", json={"code": "x"}, headers={"x-forwarded-for": f"7.7.7.{i}"})
    assert len(access_gate._wrong_attempts) <= 6  # the cap plus the shared overflow bucket


def test_a_burst_of_parallel_guesses_cannot_slip_past_the_limit(monkeypatch):
    from concurrent.futures import ThreadPoolExecutor

    client = client_with_code(monkeypatch, "pass-123")
    monkeypatch.setattr(access_gate, "_MAX_WRONG_PER_MINUTE_ALL", 20)
    with ThreadPoolExecutor(max_workers=16) as pool:
        codes = list(pool.map(lambda i: client.post("/access", json={"code": f"x{i}"}, headers={"x-forwarded-for": f"5.5.{i}.1"}).status_code, range(80)))
    assert codes.count(401) == 20  # exactly the limit, however the threads interleave
    assert codes.count(429) == 60


def test_a_right_code_is_not_counted_as_a_mistake(monkeypatch):
    client = client_with_code(monkeypatch, "pass-123")
    for _ in range(15):
        assert client.post("/access", json={"code": "pass-123"}).status_code == 200
