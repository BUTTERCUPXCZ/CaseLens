import re

from caselens.domain.digest import ParagraphRange, SectionKind
from caselens.domain.services.ruling_locator import RulingLocator

_MARKER = re.compile(r"\[\^\d+\]")
_PONENTE = re.compile(r"^.+?,\s*(?:C\.\s?)?J\.\s*:?$")  # "PEREZ, J.:" / "KHO, JR., J.:" ends the caption
_MAX_HEADING_WORDS = 10
_MAX_HEADING_CHARS = 90

# Words that make a short line a heading of the decision's own structure ("The Facts", "Ruling of the RTC",
# "The Court's Ruling", "Judgment of the Court of Appeals"). A closed list on purpose: guessing "any short
# Title Case line" cuts a section short at a table cell or a quoted heading.
_STRUCTURE_WORD = re.compile(
    r"\b(?:facts?|antecedents?|background|case|issues?|ruling|decision|judgment|resolution|proceedings|"
    r"arguments?|contentions?|discussion|errors?)\b",
    re.IGNORECASE,
)

_KINDS: dict[SectionKind, re.Pattern[str]] = {
    SectionKind.FACTS: re.compile(
        r"^(?:the\s+)?(?:(?:antecedent|background|factual|relevant|undisputed)\s+)?facts?\b"
        r"|^(?:the\s+)?antecedents?\b|^(?:the\s+)?background\b",
        re.IGNORECASE,
    ),
    SectionKind.ISSUES: re.compile(r"^(?:the\s+)?issues?\b(?!:)", re.IGNORECASE),
}


class HeadingSections:
    """Finds the sections the Court itself labelled (`The Facts`, `The Issues`) and the paragraphs under
    each, up to the next heading. No guessing: a decision with no such heading returns nothing for it.
    """

    def __init__(self, rulings: RulingLocator | None = None) -> None:
        self._rulings = rulings or RulingLocator()

    def find(self, paragraphs: list[str]) -> dict[SectionKind, ParagraphRange]:
        body_start = self.body_start(paragraphs)
        ruling = self._rulings.locate(paragraphs)
        if body_start is None:
            return {}
        body_end = (ruling.first if ruling else len(paragraphs)) - 1  # last paragraph before the final ruling
        headings = [i for i in range(body_start, body_end + 1) if self._is_heading(paragraphs[i])]

        found: dict[SectionKind, ParagraphRange] = {}
        for kind, pattern in _KINDS.items():
            heading = next((i for i in headings if pattern.match(self._plain(paragraphs[i]))), None)
            if heading is None:
                continue
            following = next((i for i in headings if i > heading), body_end + 1)
            if following - 1 >= heading + 1:
                found[kind] = ParagraphRange(heading + 1, following - 1)
        return found

    @staticmethod
    def body_start(paragraphs: list[str]) -> int | None:
        """The first paragraph after the ponente's line (`PEREZ, J.:`), i.e. after the caption."""
        index = next((i for i, text in enumerate(paragraphs[:25]) if _PONENTE.match(text)), None)
        return None if index is None else index + 1

    @staticmethod
    def _plain(text: str) -> str:
        return _MARKER.sub("", text).strip()

    def _is_heading(self, text: str) -> bool:
        plain = self._plain(text)
        return (
            0 < len(plain) <= _MAX_HEADING_CHARS
            and len(plain.split()) <= _MAX_HEADING_WORDS
            and plain[0].isupper()
            and plain[-1] not in ".:;,?"
            and _STRUCTURE_WORD.search(plain) is not None
        )
