"""Which case a file IS: the G.R. number(s) printed in its caption, and nothing else.

A decision cites dozens of other cases in its text. Reading those would turn one upload into many rows, so only the caption (the first lines,
before the ponente's line or the "DECISION" title) is read. If the caption has no G.R. number the file is reported as unreadable, never guessed."""
import re
from dataclasses import dataclass

from caselens.domain.services.citation_extractor import GR_LINE_PATTERN, GR_NUMBER_ITEM
from caselens.domain.value_objects import GrNumber

_CAPTION_LINES = 30
_LINE_START_SLACK = 3  # a bracket and a space may come before the number
# A digest's citation line may put the reporter first: "177 SCRA 668, G.R. No. 88211, September 15, 1989". That is still the case's own number.
_REPORTER_FIRST = re.compile(r"^\s*\d{1,4}\s+(?:SCRA|Phil\.?|O\.\s?G\.)\s+\d{1,5}(?:-\d{1,5})?\s*[,;:]?\s*$", re.IGNORECASE)
_YEAR = re.compile(r"\b((?:19|20)\d\d)\b")
_SHORT_RANGE = re.compile(r"\b(\d{3,7})-(\d{1,3})\b")  # "148271-72" prints the numbers 148271 to 148272
_ENDS_CAPTION = re.compile(r"^(?:[A-Z][A-Z'’\-. ]*,\s*(?:C\.?\s?J\.?|J\.?)\s*:?|(?:[A-Z] ){3,}[A-Z]|DECISION|RESOLUTION)$")


@dataclass(frozen=True)
class Identification:
    gr_numbers: tuple[GrNumber, ...]  # the main number first; a joint decision prints several
    year: int | None  # the year printed on the same line, a hint if the number is not on Lawphil's list
    problem: str | None = None  # why nothing could be read, in plain words
    reporter: str | None = None  # the reporter citation printed before the number ("177 SCRA 668"), if any

    @property
    def main(self) -> GrNumber | None:
        return self.gr_numbers[0] if self.gr_numbers else None


class MainCaseIdentifier:
    def identify(self, text: str) -> Identification:
        lines = [line.strip() for line in (text or "").splitlines() if line.strip()][:_CAPTION_LINES]
        numbers: list[GrNumber] = []
        year: int | None = None
        reporter: str | None = None
        for line in lines:
            if numbers and _ENDS_CAPTION.match(line):
                break  # the caption is over: what follows is the decision's own text
            match = GR_LINE_PATTERN.search(line)
            if match is None or (match.start() > _LINE_START_SLACK and not _REPORTER_FIRST.match(line[: match.start()])):
                continue  # a caption line BEGINS with the number ("G.R. No. 88211 ...", "[ G.R. Nos. ... ]"), or only a reporter citation comes first; "See G.R. No. ..." is a mention
            if reporter is None and match.start() > _LINE_START_SLACK:
                reporter = line[: match.start()].strip().rstrip(",;:").strip()
            for item in GR_NUMBER_ITEM.findall(match.group("nums")):
                try:
                    number = GrNumber(item)
                except ValueError:
                    continue
                if number not in numbers:
                    numbers.append(number)
            for short in _SHORT_RANGE.finditer(match.group("nums") + line[match.end() : match.end() + 12]):
                first, tail = short.group(1), short.group(2)
                last = int(first[: len(first) - len(tail)] + tail)
                for value in range(int(first), min(last, int(first) + 20) + 1):
                    number = GrNumber(str(value))
                    if number not in numbers:
                        numbers.append(number)
            if year is None and (found := _YEAR.search(line[match.end():])):
                year = int(found.group(1))
        if not numbers:
            return Identification((), None, "We could not read a G.R. number in the first lines of this file. Is it a decision?")
        return Identification(tuple(numbers), year, reporter=reporter)


_DIGEST_HEADING = re.compile(r"^\s*digest\s*\d*\s*[:.\-–]", re.IGNORECASE)  # "Digest 1: Facts and Doctrine"
_LINES_AFTER_HEADING = 3  # the case's citation sits right under the box's heading
_YEAR_IN_PARENS = re.compile(r"\((?:[A-Za-z]+\.?\s+\d{1,2},?\s+)?((?:19|20)\d\d)\)")


@dataclass(frozen=True)
class ReviewerCase:
    """A case a student's reviewer digests: the citation under one of its "Digest N:" boxes."""

    gr_no: GrNumber
    title: str  # "Review Center v Ermita"
    year: int | None  # the year the student wrote, a hint only (the student may have it wrong; the official decision decides)
    reporter: str | None  # "538 SCRA 428"


class ReviewerCaseFinder:
    """Which cases a reviewer (study notes with "Digest 1: Facts and Doctrine" boxes) asks to digest: the citation right under each box's heading.
    A case boxed twice is one case. Cases the notes only mention elsewhere are not read."""

    def find(self, text: str) -> list[ReviewerCase]:
        lines = [line.replace("\u200b", "").strip() for line in (text or "").splitlines()]
        lines = [line for line in lines if line]
        found: dict[str, ReviewerCase] = {}
        for i, line in enumerate(lines):
            if not _DIGEST_HEADING.match(line):
                continue
            for candidate in lines[i + 1 : i + 1 + _LINES_AFTER_HEADING]:
                match = GR_LINE_PATTERN.search(candidate)
                if match is None:
                    continue
                number = next((GrNumber(n) for n in GR_NUMBER_ITEM.findall(match.group("nums")) if _valid(n)), None)
                if number is None:
                    break
                before = candidate[: match.start()].strip().rstrip(",;:").strip()
                title, _, reporter = before.partition(",")
                year = _YEAR_IN_PARENS.search(candidate[match.end() :])
                found.setdefault(
                    number.value,
                    ReviewerCase(number, title.strip() or number.value, int(year.group(1)) if year else None, reporter.strip().rstrip(",") or None),
                )
                break
        return list(found.values())


def _valid(item: str) -> bool:
    try:
        GrNumber(item)
    except ValueError:
        return False
    return True
