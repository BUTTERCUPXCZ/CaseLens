"""The SC E-Library's addresses for Supreme Court decisions (shelf 1 of "the bookshelf").

    monthly list   /thebookshelf/docmonth/Mar/2015/1
    a decision     /thebookshelf/showdocs/1/60169
"""
import re
from urllib.parse import urlparse

MONTH_NAMES = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
_DECISION_PATH = re.compile(r"^/thebookshelf/showdocs/1/(\d+)/?$")


class ElibraryUrlScheme:
    def __init__(self, base_url: str) -> None:
        self._base = base_url.rstrip("/")
        self._host = urlparse(self._base).netloc.lower()

    def month_list_url(self, year: int, month: int) -> str:
        return f"{self._base}/thebookshelf/docmonth/{MONTH_NAMES[month - 1]}/{year}/1"

    def decision_url(self, doc_id: int | str) -> str:
        return f"{self._base}/thebookshelf/showdocs/1/{doc_id}"

    def is_official_case_url(self, url: str) -> bool:
        parts = urlparse(url)
        return parts.scheme == "https" and parts.netloc.lower() == self._host and bool(_DECISION_PATH.match(parts.path))

    def canonical(self, url: str) -> str:
        """The decision's address as stored (the same page reached by a printer-friendly or trailing-slash link)."""
        match = _DECISION_PATH.match(urlparse(url).path.replace("/showdocsfriendly/", "/showdocs/"))
        return self.decision_url(match.group(1)) if match else url
