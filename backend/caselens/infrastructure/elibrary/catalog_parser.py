import re
from datetime import date, datetime

from selectolax.parser import HTMLParser

from caselens.application.ports.catalog import CatalogIndexParser, ParsedIndex
from caselens.domain.entities import CatalogEntry
from caselens.domain.services.gr_label import GrLabelReader
from caselens.domain.value_objects import GrNumber
from caselens.infrastructure.elibrary.url_scheme import ElibraryUrlScheme

SOURCE = "elibrary"
_DATE = re.compile(r"([A-Z][a-z]+\.? \d{1,2}, \d{4})")
_JOINED_NUMBER = re.compile(r"\[\s*(G\.R\. Nos?\.[^\]]+)\]", re.I)  # "[G.R. No. 171217]" inside the title of a joint decision
_KIND = re.compile(r"^([A-Za-z.]+(?: [A-Z]{2,})?)")  # "A.C.", "A.M.", "B.M.", "OCA IPI"
TITLE_LIMIT = 400  # some captions name every party of a joint case (tens of thousands of characters); the list keeps the start


def short_title(title: str) -> str:
    """The title as the list keeps it: whole when short, else cut at a word before TITLE_LIMIT characters, with an ellipsis."""
    if len(title) <= TITLE_LIMIT:
        return title
    return title[:TITLE_LIMIT].rsplit(" ", 1)[0].rstrip(" ,;") + " …"


class ElibraryCatalogParser(CatalogIndexParser):
    """Reads one of the E-Library's monthly lists of Supreme Court decisions (`/thebookshelf/docmonth/Mar/2015/1`).

    Each decision is a link to `/thebookshelf/showdocs/1/<id>` holding the number in `<STRONG>` ("G.R. No. 193038",
    "G.R. Nos. 211789-90"), the title in `<small>` (a joint decision adds "[G.R. No. 171217] OTHER PARTIES ..."), and the date.
    Only G.R. cases are returned, as from Lawphil's lists; A.C., A.M., B.M. and OCA IPI matters are counted and skipped."""

    def __init__(self, scheme: ElibraryUrlScheme, label_reader: GrLabelReader | None = None) -> None:
        self._scheme = scheme
        self._labels = label_reader or GrLabelReader()

    def parse(self, html: str, index_url: str) -> ParsedIndex:
        entries: list[CatalogEntry] = []
        other_kinds: dict[str, int] = {}
        link_rows = unreadable = 0
        for anchor in HTMLParser(html).css("a[href]"):
            href = anchor.attributes.get("href") or ""
            if not self._scheme.is_official_case_url(href):
                continue
            link_rows += 1
            label = self._text(anchor.css_first("strong"))
            if not label.upper().startswith("G.R."):
                kind = _KIND.match(label)
                key = re.sub(r"[^a-z]", "", kind.group(1).lower()) if kind else "other"
                other_kinds[key] = other_kinds.get(key, 0) + 1
                continue
            entry = self._entry(anchor, label, href, index_url)
            if entry is None:
                unreadable += 1
            else:
                entries.append(entry)
        return ParsedIndex(entries, link_rows, other_kinds, unreadable)

    def _entry(self, anchor, label: str, href: str, index_url: str) -> CatalogEntry | None:
        numbers = list(self._labels.read(label)[0])
        caption = self._text(anchor.css_first("small"))
        for joined in _JOINED_NUMBER.findall(caption):  # the other numbers of a joint decision
            numbers += [n for n in self._labels.read(joined)[0] if n not in numbers]
        if not numbers:
            return None
        try:
            gr_no = GrNumber(numbers[0])
        except ValueError:
            return None
        small = anchor.css_first("small")
        after = anchor.text(separator=" ").replace(small.text(separator=" "), " ") if small else anchor.text(separator=" ")
        found = _DATE.search(after)
        return CatalogEntry(
            gr_no=gr_no,
            numbers=tuple(numbers),
            title=short_title(_JOINED_NUMBER.split(caption)[0].strip() or caption),
            decision_date=_parse_date(found.group(1)) if found else None,
            source_url=self._scheme.canonical(href),
            index_url=index_url,
            source=SOURCE,
        )

    @staticmethod
    def _text(node) -> str:
        return " ".join(node.text(separator=" ").split()) if node is not None else ""


def _parse_date(text: str) -> date | None:
    text = text.replace(".", "")
    for fmt in ("%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None
