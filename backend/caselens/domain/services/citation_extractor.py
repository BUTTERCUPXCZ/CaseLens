"""Finds G.R. citations in a student's document.

Works on text that still has its line breaks: a citation usually sits on its own
line ("Review Center v Ermita, 538 SCRA 428, GR no 180046 (April 2, 2010)"), and the
line start is how the case title is told apart from surrounding notes.
"""
import re
from datetime import date

from caselens.domain.value_objects import ClaimedCitation, GrNumber

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
_MONTH = (
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|"
    r"Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
)
_NUM = r"(?:L-?\d{3,6}|\d{3,7})"
# Items after the first must not look like a year, so "G.R. No. 180046, 2010" stays one number.
_NEXT_NUM = rf"(?!(?:19|20)\d\d\b){_NUM}"

_GR = re.compile(
    rf"\bG\.?\s?R\.?(?![A-Za-z])\s*(?:Nos?\.?)?\s*:?\s*"
    rf"(?P<nums>{_NUM}(?:\s*(?:,|and|&)\s*{_NEXT_NUM})*)",
    re.IGNORECASE,
)
_NUM_ITEM = re.compile(_NUM, re.IGNORECASE)

_DATE_TAIL = re.compile(
    rf"^[\s,;(]*(?:dated\s+)?(?:"
    rf"(?P<m1>{_MONTH})\.?\s+(?P<d1>\d{{1,2}}),?\s+(?P<y1>\d{{4}})"
    rf"|(?P<d2>\d{{1,2}})\s+(?P<m2>{_MONTH})\.?,?\s+(?P<y2>\d{{4}})"
    rf"|\(\s*(?P<y3>(?:19|20)\d\d)\s*\)"
    rf")",
    re.IGNORECASE,
)
_TITLE = re.compile(
    r"(?P<title>[A-Z][^,\n]*?\s(?:v\.|vs\.|v|vs)\s[^,\n]+?)\s*(?:,|$)"
)
_REPORTER = re.compile(r"\b(\d{1,4})\s+(SCRA|Phil\.?)\s+(\d{1,4})\b")

_ZERO_WIDTH = re.compile("[​‌‍⁠﻿]")
_TITLE_WINDOW = 200


class GrCitationExtractor:
    def extract(self, text: str) -> list[ClaimedCitation]:
        text = _ZERO_WIDTH.sub("", text)
        found: list[ClaimedCitation] = []
        seen: set[tuple] = set()

        for match in _GR.finditer(text):
            window = self._line_window(text, match.start())
            title = self._title(window)
            reporter = self._reporter(window)
            claimed_date, claimed_year = self._date(text[match.end() : match.end() + 60])

            for number in _NUM_ITEM.findall(match.group("nums")):
                citation = ClaimedCitation(
                    gr_number=GrNumber(number),
                    raw=text[match.start() : match.end()].strip(),
                    title=title,
                    claimed_date=claimed_date,
                    claimed_year=claimed_year,
                    reporter=reporter,
                )
                key = (citation.gr_number, claimed_year, (title or "").lower())
                if key not in seen:
                    seen.add(key)
                    found.append(citation)
        return found

    @staticmethod
    def _line_window(text: str, end: int) -> str:
        start = text.rfind("\n", 0, end) + 1
        return text[max(start, end - _TITLE_WINDOW) : end]

    @staticmethod
    def _title(window: str) -> str | None:
        match = _TITLE.search(window)
        return match.group("title").strip() if match else None

    @staticmethod
    def _reporter(window: str) -> str | None:
        match = _REPORTER.search(window)
        return " ".join(match.groups()) if match else None

    @staticmethod
    def _date(tail: str) -> tuple[date | None, int | None]:
        match = _DATE_TAIL.match(tail)
        if not match:
            return None, None
        if match.group("y3"):
            return None, int(match.group("y3"))
        month, day, year = (
            (match.group("m1"), match.group("d1"), match.group("y1"))
            if match.group("m1")
            else (match.group("m2"), match.group("d2"), match.group("y2"))
        )
        try:
            return date(int(year), _MONTHS[month[:3].lower()], int(day)), int(year)
        except ValueError:  # e.g. "February 31, 2010": keep the year, drop the bad date
            return None, int(year)


# Public names for the two patterns other readers of a G.R. line need (the main-case identifier reads a decision's caption with them).
GR_LINE_PATTERN = _GR
GR_NUMBER_ITEM = _NUM_ITEM
