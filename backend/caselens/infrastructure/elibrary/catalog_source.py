from collections.abc import Callable
from datetime import date

from caselens.application.ports.catalog import IndexFetcher, YearDiscovery
from caselens.domain.entities import IndexPage
from caselens.infrastructure.elibrary.catalog_parser import SOURCE
from caselens.infrastructure.elibrary.url_scheme import ElibraryUrlScheme
from caselens.infrastructure.lawphil.http_client import ThrottledPageClient


class ElibraryIndexFetcher(IndexFetcher):
    """Downloads the E-Library's monthly lists through its own throttled client (one request a second)."""

    def __init__(self, pages: ThrottledPageClient) -> None:
        self._pages = pages

    def fetch(self, url: str) -> str | None:
        return self._pages.get_text(url)


class ElibraryYearDiscovery(YearDiscovery):
    """The E-Library has a list page for every month (an empty month is an empty list), so the months are known without asking:
    January of `first_year` up to the current month. Nothing is downloaded here."""

    def __init__(self, scheme: ElibraryUrlScheme, first_year: int, today: Callable[[], date] = date.today) -> None:
        self._scheme = scheme
        self._first_year = first_year
        self._today = today

    def years(self) -> list[int]:
        return list(range(self._first_year, self._today().year + 1))

    def months(self, year: int) -> list[IndexPage]:
        today = self._today()
        last = today.month if year == today.year else 12
        return [IndexPage(year, month, self._scheme.month_list_url(year, month), SOURCE) for month in range(1, last + 1)]
