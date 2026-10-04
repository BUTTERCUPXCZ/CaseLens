import re
from datetime import date

from caselens.domain.value_objects import GrNumber

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
# Real month names only: a looser "Word 12, 2009" pattern swallowed "Nos. 211972" as a date.
_MONTH_NAMES = (
    r"Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|Aug(?:ust)?|"
    r"Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?"
)
_DATE = re.compile(rf"\b({_MONTH_NAMES})\.?\s+(\d{{1,2}}),?\s*(\d{{4}})\b")
# "180046", "L-28156", and ranges "148271-72" / "211733-34" (suffix shorter than the start).
_NUMBER = re.compile(r"(?<![\w-])(L-?\d{3,6}|\d{3,7})(?:-(\d{2,7}))?(?![\w])", re.IGNORECASE)
_MAX_RANGE = 50  # "100000-100999" is a typo, not 1,000 cases


class GrLabelReader:
    """Reads the first cell of a Lawphil list row: the G.R. numbers and the decision date.

    Real labels seen on the site: `G.R. No. 180923`, `G.R. Nos. 211972 & 212045`,
    `G.R. No. 148263 and 148271-72`, `G.R. No. 164785 G.R. No. 165636`,
    `G.R. No. 209353-54/G.R. Nos. 211733-34`, `G.R. No. L-28156`, and dates with or without
    the space after the comma (`March 31,1987`)."""

    def read(self, label: str) -> tuple[tuple[str, ...], date | None]:
        text = " ".join(label.split())
        decided = self._date(text)
        without_date = _DATE.sub(" ", text)
        return self._numbers(without_date), decided

    @staticmethod
    def _date(text: str) -> date | None:
        for match in _DATE.finditer(text):
            month = _MONTHS.get(match.group(1)[:3].lower())
            if month is None:
                continue
            try:
                return date(int(match.group(3)), month, int(match.group(2)))
            except ValueError:
                continue
        return None

    @staticmethod
    def _numbers(text: str) -> tuple[str, ...]:
        found: list[str] = []
        for match in _NUMBER.finditer(text):
            start, end = match.group(1), match.group(2)
            numbers = [start]
            if end:
                numbers = GrLabelReader._expand(start, end)
            for raw in numbers:
                try:
                    value = GrNumber(raw).value
                except ValueError:
                    continue
                if value not in found:
                    found.append(value)
        return tuple(found)

    @staticmethod
    def _expand(start: str, end: str) -> list[str]:
        """`148271` + `72` -> 148271, 148272.  `L-12091` + `92` -> L-12091, L-12092."""
        prefix = "L-" if start.upper().startswith("L") else ""
        digits = start.upper().lstrip("L-")
        low = int(digits)
        # a short suffix replaces the last digits of the start; a full-length one is the end itself
        high = int(digits[: len(digits) - len(end)] + end) if len(end) < len(digits) else int(end)
        if high < low or high - low >= _MAX_RANGE:
            return [start]  # not a range after all (e.g. a number joined to a case number)
        return [f"{prefix}{n}" for n in range(low, high + 1)]
