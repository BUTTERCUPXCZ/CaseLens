"""Finds the Court's own statement of the Issue in a decision the Court did not label.

Rules only, no AI, nothing generated: every result is a range of paragraphs of the stored decision, so the text shown
is always the Court's. The rules are deliberately narrow: a missed passage costs the student one click ("Pick
paragraphs"), a wrong one wastes their trust, so when unsure they return nothing. They were tuned on the hand-marked
decisions in `tests/fixtures/digest/gold.json`: no wrong suggestion there.

There is no rule for the Facts: "everything before the issue" was tried on the same decisions and took in the introduction and
the lower courts' rulings (1 of 15 stayed inside the hand-marked Facts). The Facts are picked by the AI step instead.
"""
import re
from dataclasses import dataclass

from caselens.domain.digest import ParagraphRange

_ADJECTIVE = (
    r"(?:sole|single|only|main|principal|primary|basic|threshold|singular|lone|key|central|crucial|legal|real|first|"
    r"ultimate|pivotal)"
)
# Words that may open the paragraph before the cue ("Hence, this petition ...", "In this appeal, ...").
_LEAD = r"^(?:(?:hence|thus|now|here|therefore|[^,.]{0,60}\b(?:petition|appeal|certiorari|case)\b[^,.]{0,40}),?\s+)?"
_RAISES = r"(?:raises?|presents?|poses?|submits?|assigns?|posits?|positing|assigning|raising)"

_CUES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("\"At issue\"", re.compile(r"^at issue\b", re.IGNORECASE)),
    (
        "\"The issue is\"",
        re.compile(
            _LEAD
            + rf"(?:the|this|its|their|our)\s+(?:{_ADJECTIVE}\s+)*(?:issues?|questions?)\b[^.:]{{0,160}}"
            r"\b(?:is|are|here|presented|raised|posited|advanced|before|for)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "\"raises the following issues\"",
        re.compile(
            rf"\b{_RAISES}\b[^.:]{{0,60}}\bfollowing\s+(?:issues?|questions?|errors?|assignments? of errors?|"
            r"contentions|points|propositions)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "\"the following issues:\"",
        re.compile(r"\bthe following\s+(?:issues?|questions?|errors?|assignments? of errors?)\b[^.]{0,80}:$", re.IGNORECASE),
    ),
    (
        "\"we are called upon to\"",
        re.compile(r"^(?:[^,.]{0,60},\s+)?we are (?:now )?(?:called|asked|tasked) (?:upon )?to\b", re.IGNORECASE),
    ),
)
# Not a statement of the issue even if it names one: the Court is passing over it, or quoting a lower court.
_NOT_AN_ISSUE = re.compile(r"\bnot (?:novel|new)\b|\b(?:is|was|been|already) (?:long )?settled\b|\beclipsed\b|\bwhile the issue\b", re.IGNORECASE)
# A line that only labels the section ("Assignment of Error", "The Issue"): the statement is the next paragraph.
_SECTION_LABEL = re.compile(
    r"^(?:assignments? of errors?|errors? (?:assigned|complained of)|statement of (?:the )?issues?|questions? presented|"
    r"issues? for resolution|the issues?(?: before the court)?|issues?|arguments)\s*:?$",
    re.IGNORECASE,
)
# The lines that belong to a list of issues: "1.", "a.", "(2)", "Whether ...", or a line in CAPITALS (an assigned error).
_LIST_ITEM = re.compile(
    r'^["“]?\s*(?:[IVX]{1,4}\.?|\d{1,2}[.)]|\(?[a-z]\)|\([a-z0-9]\)|[a-z]\.)\s|^whether\b', re.IGNORECASE
)
_CAPITALS_LINE = re.compile(r'^["“]?[A-Z][A-Z ,.\'’\-]{25,}$')  # case-sensitive on purpose: an ordinary sentence is not a list item
_ITEM_MARK = re.compile(r"^(?:[IVX]{1,4}\.?|\(?[a-z0-9]{1,2}[.)])$", re.IGNORECASE)  # a line that is only "I" or "(a)"

_MAX_STATEMENT_CHARS = 450  # a longer paragraph is narrative, not a statement of the issue
_MAX_LIST = 16  # items after the statement
_SEARCH_PARAGRAPHS = 130  # the issue is stated near the start of the body
_LONG_RANGE = 6  # a labelled Issue longer than this has probably run on into the discussion


@dataclass(frozen=True)
class Suggestion:
    range: ParagraphRange
    reason: str  # for the audit log: which cue or heading it came from


def _is_label(text: str) -> bool:
    return bool(_SECTION_LABEL.match(text.strip()))


def _is_list_line(text: str) -> bool:
    text = text.strip()
    return bool(text) and bool(_LIST_ITEM.match(text) or _CAPITALS_LINE.match(text) or _ITEM_MARK.match(text))


def _continue_list(paragraphs: list[str], first: int, end: int) -> int:
    """The last paragraph of the list that starts right after `first` (or `first` itself if none follows)."""
    last, index = first, first + 1
    while index < end and index - first <= _MAX_LIST and _is_list_line(paragraphs[index]):
        last, index = index, index + 1
    return last


class IssueFinder:
    def find(self, paragraphs: list[str], body_start: int | None, ruling_first: int | None) -> Suggestion | None:
        """The Court's own statement of the issue, for a decision with no Issue heading. None if the Court does not
        state one in words this recognises."""
        if body_start is None:
            return None
        end = ruling_first if ruling_first is not None else len(paragraphs)
        for index in range(body_start, min(end, body_start + _SEARCH_PARAGRAPHS)):
            text = paragraphs[index].strip()
            if not text or len(text) > _MAX_STATEMENT_CHARS or _NOT_AN_ISSUE.search(text[:250]) or _is_label(text):
                continue
            for label, pattern in _CUES:
                if pattern.search(text[:300]):
                    return Suggestion(ParagraphRange(index, _continue_list(paragraphs, index, end)), f"cue: {label}")
        return None

    def cap(self, paragraphs: list[str], labelled: ParagraphRange) -> ParagraphRange:
        """A labelled Issue runs to the next heading it recognises. Where it recognises none, the range runs into the
        discussion (88 paragraphs in one decision). Keep the statement, its lead-in and the list of questions."""
        if len(labelled) <= _LONG_RANGE:
            return labelled
        last = labelled.first
        for index in range(labelled.first + 1, labelled.last + 1):
            text = paragraphs[index].strip()
            lead_in = index == labelled.first + 1 and (text.endswith(":") or "following" in text.lower())
            if _is_list_line(text) or lead_in:
                last = index
            else:
                break
        return ParagraphRange(labelled.first, last)
