import re
from urllib.parse import urljoin

from selectolax.parser import HTMLParser

from caselens.application.ports.catalog import CatalogIndexParser, ParsedIndex
from caselens.domain.entities import CatalogEntry
from caselens.domain.services.gr_label import GrLabelReader
from caselens.domain.value_objects import GrNumber

_KIND = re.compile(r"^([a-z]+)_")
_LINK_NUMBER = re.compile(r"l-?\d+|\d+", re.IGNORECASE)


class LawphilCatalogParser(CatalogIndexParser):
    """Reads a Lawphil monthly list (`/judjuris/juri2009/apr2009/apr2009.html`).

    The page is a table inside a wrapper table. A case row has no table inside and at least two
    cells: `G.R. No. N <br> date`, `Party vs. Party`, and (on newer pages) a PDF-icon cell. The
    wrapper row holds the whole page, so it is skipped by requiring *no nested table*. Only G.R. cases are returned; A.M., A.C.
    and B.M. rows are counted but skipped (administrative and bar matters, out of scope)."""

    def __init__(self, label_reader: GrLabelReader | None = None) -> None:
        self._labels = label_reader or GrLabelReader()

    def parse(self, html: str, index_url: str) -> ParsedIndex:
        entries: list[CatalogEntry] = []
        other_kinds: dict[str, int] = {}
        link_rows = unreadable = 0

        for row in HTMLParser(html).css("tr"):
            cells = [child for child in row.iter() if child.tag == "td"]
            if len(cells) < 2 or row.css_first("table") is not None:
                continue
            anchor = cells[0].css_first("a[href]")
            if anchor is None:
                continue
            href = anchor.attributes.get("href") or ""
            kind = _KIND.match(href.rsplit("/", 1)[-1].lower())
            if kind is None:
                continue
            link_rows += 1
            if kind.group(1) != "gr":
                other_kinds[kind.group(1)] = other_kinds.get(kind.group(1), 0) + 1
                continue

            entry = self._entry(cells, href, index_url)
            if entry is None:
                unreadable += 1
            else:
                entries.append(entry)

        return ParsedIndex(entries, link_rows, other_kinds, unreadable)

    def _entry(self, cells, href: str, index_url: str) -> CatalogEntry | None:
        numbers, decided = self._labels.read(self._text(cells[0]))
        link_number = self._link_number(href)
        if not numbers or link_number is None:
            return None
        return CatalogEntry(
            gr_no=link_number,
            numbers=numbers,
            title=self._text(cells[1]),
            decision_date=decided,
            source_url=urljoin(index_url, href),
            index_url=index_url,
        )

    @staticmethod
    def _link_number(href: str) -> GrNumber | None:
        """`gr_l-12091-92_1960.html` -> L-12091 (the first number in the file name)."""
        name = href.rsplit("/", 1)[-1].lower().removeprefix("gr_")
        match = _LINK_NUMBER.match(name)
        if not match:
            return None
        try:
            return GrNumber(match.group(0))
        except ValueError:
            return None

    @staticmethod
    def _text(node) -> str:
        return " ".join(node.text(separator=" ").split())
