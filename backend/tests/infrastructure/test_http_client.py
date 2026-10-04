import httpx
import pytest

from caselens.domain.errors import SourceUnavailableError
from caselens.infrastructure.lawphil.http_client import ThrottledPageClient


class FakeTime:
    """Virtual clock: sleeping advances time instantly, so tests never really wait."""

    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def clock(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def make_client(handler, time: FakeTime, interval=1.0, retries=2) -> ThrottledPageClient:
    http = httpx.Client(transport=httpx.MockTransport(handler))
    return ThrottledPageClient(http, interval, retries, sleep=time.sleep, clock=time.clock)


def test_returns_body_on_200():
    time = FakeTime()
    client = make_client(lambda r: httpx.Response(200, text="hello"), time)
    assert client.get_text("https://lawphil.net/x") == "hello"


def test_page_declared_windows_1252_in_its_meta_tag_is_not_damaged():
    """The way Lawphil serves pages: no charset in the header, windows-1252 in the page."""
    page = b'<meta http-equiv="content-type" content="text/html; charset=windows-1252">OSG\x92s Technical Objections'
    client = make_client(lambda r: httpx.Response(200, content=page, headers={"content-type": "text/html"}), FakeTime())

    text = client.get_text("https://lawphil.net/x")

    assert text.endswith("OSG’s Technical Objections")
    assert "�" not in text


def test_404_is_none_not_an_error():
    client = make_client(lambda r: httpx.Response(404), FakeTime())
    assert client.get_text("https://lawphil.net/x") is None


def test_retries_503_then_succeeds_with_backoff():
    time, calls = FakeTime(), []

    def handler(request):
        calls.append(1)
        return httpx.Response(503) if len(calls) == 1 else httpx.Response(200, text="ok")

    assert make_client(handler, time).get_text("https://lawphil.net/x") == "ok"
    assert len(calls) == 2
    assert time.sleeps == [1]  # first backoff; the throttle needed no extra wait


def test_gives_up_after_max_retries():
    time, calls = FakeTime(), []

    def handler(request):
        calls.append(1)
        return httpx.Response(500)

    with pytest.raises(SourceUnavailableError, match="3 attempts"):
        make_client(handler, time, retries=2).get_text("https://lawphil.net/x")
    assert len(calls) == 3
    assert time.sleeps == [1, 2]  # exponential backoff


def test_other_errors_are_not_retried():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(403)

    with pytest.raises(SourceUnavailableError, match="403"):
        make_client(handler, FakeTime()).get_text("https://lawphil.net/x")
    assert len(calls) == 1


def test_network_errors_are_retried():
    calls = []

    def handler(request):
        calls.append(1)
        if len(calls) == 1:
            raise httpx.ConnectError("boom")
        return httpx.Response(200, text="ok")

    assert make_client(handler, FakeTime()).get_text("https://lawphil.net/x") == "ok"


def test_requests_are_spaced_by_the_minimum_interval():
    time = FakeTime()
    client = make_client(lambda r: httpx.Response(200, text="ok"), time, interval=1.0)
    client.get_text("https://lawphil.net/a")
    client.get_text("https://lawphil.net/b")
    assert time.sleeps == [1.0]  # no wait before the first request, one full interval before the second
