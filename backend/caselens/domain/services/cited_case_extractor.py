"""Finds the cases a decision cites ("Ople v. Torres", "LPBS Commercial, Inc. v. Amila, G.R. No. 147443").

Footnotes are the high-precision source: each one is split into citation segments and
the title is cut before the reporter ("G.R. No." / "123 Phil.") that follows it.
Body prose is matched with a stricter "Capitalised v. Capitalised" pattern.
"""
import re

from caselens.domain.entities import CitedCase

_V = r"\sv(?:s)?\.\s"
_SEGMENT_SPLIT = re.compile(
    r"\s*(?:;|\bciting\b|\bSee also\b:?|\bSee\b:?|\bsupra\b)\s*", re.IGNORECASE
)
_TITLE_END = re.compile(r",\s*(?:G\.R\. Nos?\.|\d+\s+(?:Phil\.?|SCRA)\b)")
_GR = re.compile(r"G\.R\. Nos?\.\s*(L-?\d{3,6}|\d{3,7})")

_WORD = r"[A-Z][\w\.'\-]*"
_BODY_CASE = re.compile(
    rf"(?<![\w])({_WORD}(?:\s+(?:{_WORD}|&|of|the|ng|mga|de|del))*?)"
    rf"\s+v(?:s)?\.\s+({_WORD}(?:\s+(?:{_WORD}|&|of|the))*)"
)
_LEADING_STOPWORDS = {"In", "See", "The", "Under", "Thus", "Like", "As", "Per", "Citing"}
_ABBREVIATIONS = {"Inc", "Co", "Corp", "Ltd", "Jr", "Sr", "Bros", "Atty", "Hon", "al"}  # "et al."


class CitedCaseExtractor:
    def extract(self, body_text: str, footnotes: list[tuple[int, str]]) -> list[CitedCase]:
        """`footnotes` are (number, text) pairs; the number lets a result link to its footnote."""
        found: list[CitedCase] = []
        for number, text in footnotes:
            found.extend(self._from_footnote(number, text))
        found.extend(self._from_body(body_text))
        return self._deduplicate(found)

    def _from_footnote(self, number: int, text: str) -> list[CitedCase]:
        cases = []
        for segment in _SEGMENT_SPLIT.split(text):
            segment = segment.strip()
            if not re.search(_V, segment) or not segment[:1].isupper():
                continue
            end = _TITLE_END.search(segment)
            title = segment[: end.start()] if end else segment
            title = self._trim(title)
            gr = _GR.search(segment)
            cases.append(CitedCase(title, gr.group(1) if gr else None, "footnote", number))
        return cases

    @staticmethod
    def _trim(title: str) -> str:
        """Drop trailing commas/spaces and a sentence-ending period, but keep the
        period of an abbreviation ("Inc.", "Co.", "Jr.") that is part of the name."""
        title = title.strip(" ,")
        if title.endswith(".") and title[:-1].split()[-1] not in _ABBREVIATIONS:
            title = title[:-1].rstrip(" ,")
        return title

    def _from_body(self, text: str) -> list[CitedCase]:
        cases = []
        for m in _BODY_CASE.finditer(text):
            left, right = m.group(1).split(), m.group(2)
            while left and left[0] in _LEADING_STOPWORDS:
                left = left[1:]
            if left:
                cases.append(CitedCase(f"{' '.join(left)} v. {right}", None, "body"))
        return cases

    @staticmethod
    def _deduplicate(cases: list[CitedCase]) -> list[CitedCase]:
        unique: dict[str, CitedCase] = {}
        for case in cases:
            key = re.sub(r"\s+v(?:s)?\.\s+", " v. ", case.title).lower()
            existing = unique.get(key)
            if existing is None or (existing.gr_no is None and case.gr_no):
                unique[key] = case
        return list(unique.values())
