"""Cleans text copied from Google Docs / Lawphil so it can be compared reliably.

Each cleaning step is its own small class implementing `TextRule`
(Single Responsibility). `TextNormalizer` just runs them in order, so a new
rule is added by writing a class, not by editing existing ones (Open/Closed).

Official Lawphil text is stored verbatim and never passes through this module;
it is only used on text that is *compared*.
"""
import re
from typing import Protocol


class TextRule(Protocol):
    def apply(self, text: str) -> str: ...


class ZeroWidthCharacterRule:
    """Google Docs exports leave zero-width characters that break regex and equality."""

    _PATTERN = re.compile("[​‌‍⁠﻿]")

    def apply(self, text: str) -> str:
        return self._PATTERN.sub("", text)


class LawphilWatermarkRule:
    """Lawphil injects tracking tokens such as `1awphi1` / `1avvphi1` into pasted text."""

    _PATTERN = re.compile(r"1a(?:w|vv)p(?:hi|\+\+i)1")

    def apply(self, text: str) -> str:
        return self._PATTERN.sub("", text)


class GluedFootnoteMarkerRule:
    """Removes footnote numbers glued to punctuation: `Court.21 The` -> `Court. The`.

    Only strips 1-2 digits that follow punctuation which itself follows a letter or
    closing bracket/quote. Known limitation: a marker after a digit (`2007,7 invited`)
    is ambiguous with real numbers and is left alone.
    """

    _PATTERN = re.compile(r"(?<=[A-Za-z\)\]\"”’'])([.,;:])\d{1,2}(?=\s|$)")

    def apply(self, text: str) -> str:
        return self._PATTERN.sub(r"\1", text)


class TypographyRule:
    """Unify curly quotes, dashes and non-breaking spaces."""

    _TABLE = str.maketrans(
        {
            "‘": "'",
            "’": "'",
            "“": '"',
            "”": '"',
            "–": "-",
            "—": "-",
            " ": " ",
        }
    )

    def apply(self, text: str) -> str:
        return text.translate(self._TABLE)


class WhitespaceRule:
    def apply(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()


class TextNormalizer:
    def __init__(self, rules: list[TextRule]) -> None:
        self._rules = rules

    @classmethod
    def default(cls) -> "TextNormalizer":
        return cls(
            [
                ZeroWidthCharacterRule(),
                LawphilWatermarkRule(),
                GluedFootnoteMarkerRule(),
                TypographyRule(),
                WhitespaceRule(),
            ]
        )

    def normalize(self, text: str) -> str:
        for rule in self._rules:
            text = rule.apply(text)
        return text
