import re
from collections.abc import Callable
from datetime import date

from caselens.application.ports.catalog import IndexFetcher, YearDiscovery
from caselens.domain.entities import IndexPage
from caselens.infrastructure.lawphil.http_client import ThrottledPageClient
from caselens.infrastructure.lawphil.url_scheme import MONTH_CODES, LawphilUrlScheme

_YEAR_LINK = re.compile(r"juri(\d{4})/juri\1\.html")
_EARLIEST_YEAR = 1901


class LawphilIndexFetcher(IndexFetcher):
    """Downloads list pages through the shared, throttled client (one request per second)."""

    def __init__(self, pages: ThrottledPageClient) -> None:
        self._pages = pages

    def fetch(self, url: str) -> str | None:
        return self._pages.get_text(url)


class LawphilYearDiscovery(YearDiscovery):
    """Asks Lawphil which years and months exist, instead of guessing page names.

    The master page (`/judjuris/judjuris.html`) links every year (it even links years that
    have not happened yet, which are ignored); each year page links the months that exist.
    Months can be missing (2023 has no May or September; the page still names them but without a
    link), so guessing would only produce 404s."""

    def __init__(
        self,
        pages: ThrottledPageClient,
        scheme: LawphilUrlScheme,
        base_url: str,
        today: Callable[[], date] = date.today,
    ) -> None:
        self._pages = pages
        self._scheme = scheme
        self._base = base_url.rstrip("/")
        self._today = today

    def years(self) -> list[int]:
        html = self._pages.get_text(f"{self._base}/judjuris/judjuris.html")
        if html is None:
            return []
        found = {int(y) for y in _YEAR_LINK.findall(html)}
        return sorted(y for y in found if _EARLIEST_YEAR <= y <= self._today().year)

    def months(self, year: int) -> list[IndexPage]:
        html = self._pages.get_text(f"{self._base}/judjuris/juri{year}/juri{year}.html")
        if html is None:
            return []
        # Only real links count: Lawphil writes a month that does not exist as `<xref="may2023/...">`
        # (no href), so all 12 names appear on the page. A named group keeps "\1" from being read
        # together with the year's digits as backreference 120.
        pattern = rf'href="(?P<code>[a-z]{{3}}){year}/(?P=code){year}\.html"'
        listed = {m.group("code") for m in re.finditer(pattern, html)}
        return [
            IndexPage(year, number, self._scheme.month_index_url(year, number))
            for number, code in enumerate(MONTH_CODES, start=1)
            if code in listed
        ]
