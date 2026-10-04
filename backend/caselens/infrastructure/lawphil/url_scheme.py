"""Everything we know about how Lawphil names its pages (verified against the live site).

    month index : /judjuris/juri2009/apr2009/apr2009.html      (months jan..dec)
    decision    : .../apr2009/gr_180046_2009.html
    old style   : .../jan1960/gr_l-10854_1960.html             (lowercase "l-" prefix)
    consolidated: .../jan1960/gr_l-12091-92_1960.html          (extra "-92")
    extra docs  : .../jul2015/gr_207145_so_2015.html           (suffix before the year)
"""
import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

from caselens.domain.value_objects import GrNumber

MONTH_CODES = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]

_CASE_FILE = re.compile(
    r"^gr_(?P<num>l-\d+(?:-\d+)*|\d+(?:-\d+)*)(?:_(?P<suffix>[a-z0-9_]+?))?_(?P<year>\d{4})\.html$"
)


@dataclass(frozen=True)
class CaseLink:
    url: str
    number_token: str  # as written in the file name, e.g. "l-12091-92"
    suffix: str | None  # None for the primary decision
    year: int

    def is_for(self, gr_no: GrNumber) -> bool:
        target = gr_no.value.lower()
        return self.number_token == target or self.number_token.startswith(target + "-")


class LawphilUrlScheme:
    def __init__(self, base_url: str) -> None:
        self._base = base_url.rstrip("/")
        self._host = urlparse(self._base).netloc

    def month_index_url(self, year: int, month: int) -> str:
        code = MONTH_CODES[month - 1]
        return f"{self._base}/judjuris/juri{year}/{code}{year}/{code}{year}.html"

    def case_urls_in_index(self, index_url: str, index_html: str) -> list[str]:
        hrefs = re.findall(r'href="([^"#]+\.html)"', index_html)
        urls = [urljoin(index_url, href) for href in hrefs if href.rsplit("/", 1)[-1].startswith("gr_")]
        return list(dict.fromkeys(urls))  # de-duplicate, keep order

    def parse_case_link(self, url: str) -> CaseLink | None:
        match = _CASE_FILE.match(url.rsplit("/", 1)[-1].lower())
        if not match:
            return None
        return CaseLink(url, match.group("num"), match.group("suffix"), int(match.group("year")))

    def is_official_case_url(self, url: str) -> bool:
        parsed = urlparse(url)
        return (
            parsed.scheme == "https"
            and parsed.netloc == self._host
            and parsed.path.startswith("/judjuris/")
            and parsed.path.endswith(".html")
        )
