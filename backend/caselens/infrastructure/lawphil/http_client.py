import time
from collections.abc import Callable

import httpx

from caselens.domain.errors import SourceUnavailableError
from caselens.infrastructure.config import Settings
from caselens.infrastructure.lawphil.html_decoding import decode_html

_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class ThrottledPageClient:
    """Polite HTTP client: one request per `min_interval` seconds, retry with
    exponential backoff on timeouts, 429 and 5xx. A 404 is a normal answer (None)."""

    def __init__(
        self,
        client: httpx.Client,
        min_interval: float,
        max_retries: int,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._client = client
        self._min_interval = min_interval
        self._max_retries = max_retries
        self._sleep = sleep
        self._clock = clock
        self._last_request_at: float | None = None

    @classmethod
    def from_settings(cls, settings: Settings) -> "ThrottledPageClient":
        client = httpx.Client(
            headers={"User-Agent": settings.lawphil_user_agent},
            timeout=settings.lawphil_timeout_seconds,
            follow_redirects=True,
        )
        return cls(client, settings.lawphil_min_interval_seconds, settings.lawphil_max_retries)

    def get_text(self, url: str) -> str | None:
        last_problem = "no attempt made"
        for attempt in range(self._max_retries + 1):
            self._wait_for_turn()
            try:
                response = self._client.get(url)
            except httpx.TransportError as exc:
                last_problem = f"{type(exc).__name__}: {exc}"
            else:
                if response.status_code == 200:
                    # Not response.text: that guesses UTF-8 and damages Windows-1252 pages.
                    return decode_html(response.content, response.headers.get("content-type"))
                if response.status_code == 404:
                    return None
                if response.status_code not in _RETRYABLE_STATUS:
                    raise SourceUnavailableError(f"{url} returned HTTP {response.status_code}")
                last_problem = f"HTTP {response.status_code}"

            if attempt < self._max_retries:
                self._sleep(2**attempt)  # 1s, 2s, 4s ...
        raise SourceUnavailableError(
            f"{url} failed after {self._max_retries + 1} attempts ({last_problem})"
        )

    def _wait_for_turn(self) -> None:
        if self._last_request_at is not None:
            remaining = self._last_request_at + self._min_interval - self._clock()
            if remaining > 0:
                self._sleep(remaining)
        self._last_request_at = self._clock()
