"""Sorts the sentences of a written digest before any second AI looks at them: which can be shown as they are, which are certainly
wrong, and which only a reader of meaning can judge.

Code cannot tell whether a sentence says what its paragraph means, only whether its words, numbers and names are there. So a PASS
here means "nothing for a checker to catch that code can see", never "legally right": it lets a plain sentence skip the second
model, while anything that changes the weight of a passage (an overstatement, a negation, an argument turned into a holding, a
low share of the paragraph's own words) is sent to it. INVALID sentences cannot be shown at all (a paragraph that does not exist,
a number or name the decision never mentions)."""
import re
from dataclasses import dataclass
from enum import Enum

from caselens.domain.digest import AnswerSentence, SourcePassage
from caselens.domain.digest_v2 import Section
from caselens.domain.services.answer_validator import AnswerValidator

_CITE_ID = re.compile(r"^(?:C1|P\d+|O\d+\.\d+)$")
_NUMBER = re.compile(r"\d[\d,.]*\d|\d")
_GR_NUMBER = re.compile(r"G\.\s?R\.\s*Nos?\.?\s*(L-?\d{3,6}|\d{3,7})", re.IGNORECASE)
_MONTH = r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
_DATE = re.compile(rf"\b{_MONTH}\s+\d{{1,2}},\s+\d{{4}}\b")
_WORD = re.compile(r"[a-z][a-z'’-]+")
_STOPWORDS = frozenset(
    "this that these those with from into onto upon over under about above after before between during through their there "
    "them they then than were was been being have has had having does did doing done also such which while whom whose what "
    "when where would could should shall will case court decision held ruled said stated because therefore thus however "
    "only more most some other each both very must under within without against".split()
)
_SUFFIXES = ("ations", "ation", "ments", "ment", "ings", "ing", "ions", "ion", "ies", "ied", "edly", "ed", "es", "ly", "s")
_OVERSTATEMENT = re.compile(r"\b(?:always|never|all|every|landmark|settled|absolute(?:ly)?|clearly|undoubtedly|for the first time|only)\b", re.IGNORECASE)
_NEGATION = re.compile(r"\b(?:not|no|never|neither|nor|cannot|without)\b|n['’]t\b", re.IGNORECASE)
_COURT_HOLDS = re.compile(r"\b(?:the court|the supreme court|we)\s+(?:held|holds|ruled|rules|found|finds|declared|declares|decided|decides)\b", re.IGNORECASE)
_PARTY_ARGUES = re.compile(
    r"\b(?:petitioners?|respondents?|appellants?|appellees?|accused|complainants?|the (?:solicitor general|osg))\b[^.]{0,60}?"
    r"\b(?:contends?|argues?|maintains?|claims?|avers?|insists?|asserts?|alleges?|submits?|posits?)\b",
    re.IGNORECASE,
)
_COURT_VOICE = re.compile(r"\b(?:we (?:hold|rule|find|agree|disagree|declare)|this court (?:holds|rules|finds)|the court (?:holds|rules|finds))\b", re.IGNORECASE)
_NOT_STATED = re.compile(
    r"\b(?:not|never) (?:stated|said|discussed|addressed|mentioned|given|specified|shown|explained)\b|\bdoes not (?:say|state|discuss|address|mention|specify)\b|"
    r"\bno (?:separate |dissenting )?opinions?\b",
    re.IGNORECASE,
)


class ClaimStatus(str, Enum):
    PASS = "pass"  # nothing code can see is wrong: it may skip the second model
    SUSPICIOUS = "suspicious"  # only a reader of meaning can tell: the second model judges it
    INVALID = "invalid"  # cannot be shown (a paragraph that does not exist, a number or name the decision never mentions)


@dataclass(frozen=True)
class ClaimCheck:
    status: ClaimStatus
    reason: str = ""


def _stem(word: str) -> str:
    word = word.strip("'’-")
    for suffix in _SUFFIXES:
        if len(word) - len(suffix) >= 4 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def _content_stems(text: str) -> list[str]:
    return [_stem(w) for w in _WORD.findall(text.lower()) if len(w) >= 4 and w not in _STOPWORDS]


class ClaimValidator:
    def __init__(self, coverage_min: float = 0.6, answers: AnswerValidator | None = None) -> None:
        self._coverage_min = coverage_min
        self._answers = answers or AnswerValidator()

    def classify(self, sentence: AnswerSentence, sources: dict[str, SourcePassage], section: Section | None = None) -> ClaimCheck:
        text = sentence.text.strip()
        if not text:
            return ClaimCheck(ClaimStatus.INVALID, "empty sentence")
        if not sentence.cites:
            # An honest "the decision does not say ..." has nothing to cite; it may make no other claim (no numbers).
            if _NOT_STATED.search(text) and not re.search(r"\d", text):
                return ClaimCheck(ClaimStatus.PASS)
            return ClaimCheck(ClaimStatus.INVALID, "no source cited")
        malformed = [c for c in sentence.cites if not _CITE_ID.match(c)]
        if malformed:
            return ClaimCheck(ClaimStatus.INVALID, f"not a passage id: {', '.join(malformed)}")
        problem = self._answers.check(sentence, sources, numbers_anywhere=True)  # exists, numbers and names somewhere in the decision
        if problem:
            return ClaimCheck(ClaimStatus.INVALID, problem)
        everything = " ".join(s.text for s in sources.values())
        for number in _GR_NUMBER.findall(text):
            if number not in everything:
                return ClaimCheck(ClaimStatus.INVALID, f"G.R. No. {number} is not in the decision")

        cited = " ".join(sources[c].text for c in sentence.cites)
        why = self._why_suspicious(text, cited, [sources[c].text for c in sentence.cites], section)
        return ClaimCheck(ClaimStatus.SUSPICIOUS, why) if why else ClaimCheck(ClaimStatus.PASS)

    def _why_suspicious(self, text: str, cited: str, cited_parts: list[str], section: Section | None) -> str | None:
        lowered = cited.lower()
        for number in _NUMBER.findall(text):
            if number.rstrip(".,") not in cited:
                return f"number {number} is in the decision but not in the cited text"
        for day in _DATE.findall(text):
            if day not in cited:
                return f"date {day} is not written that way in the cited text"
        for name in AnswerValidator._names(text):
            if name.lower() not in lowered and name not in ("Court", "Supreme", "Philippines", "Philippine", "Constitution", "Justice", "Justices"):
                return f"name '{name}' is not in the cited text"
        for word in {m.group(0).lower() for m in _OVERSTATEMENT.finditer(text)}:
            if word not in lowered:
                return f"'{word}' is stronger than the cited text"
        if _NEGATION.search(text) and not _NEGATION.search(cited):
            return "a negation the cited text does not have"
        if _COURT_HOLDS.search(text) and all(_PARTY_ARGUES.search(part) and not _COURT_VOICE.search(part) for part in cited_parts):
            return "says the Court held what the cited text gives as a party's argument"
        if section is Section.DISSENTS:
            justice = text.split(":", 1)[0].split(",", 1)[0].split()
            if justice and justice[-1].lower() not in lowered:
                return "the justice named is not the author of the cited opinion"
        stems = _content_stems(text)
        if stems:
            known = set(_content_stems(cited))
            share = sum(1 for s in stems if s in known) / len(stems)
            if share < self._coverage_min:
                return f"only {share:.0%} of its words are in the cited text"
        return None
