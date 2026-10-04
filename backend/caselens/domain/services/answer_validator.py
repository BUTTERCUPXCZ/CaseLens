import re

from caselens.domain.digest import AnswerSentence, SourcePassage

_NUMBER = re.compile(r"\d[\d,.]*\d|\d")
_CAPITALISED = re.compile(r"\b[A-Z][a-z]{3,}\b")
# Words that are normal in any answer about a Philippine decision, so they need not appear in the cited text.
_ALWAYS_ALLOWED = {"Court", "Supreme", "Philippines", "Philippine", "Filipino", "Constitution", "Section", "Article"}


class AnswerValidator:
    """The checks that need no AI: an answer sentence must name sources that exist; every number in it must
    be in the sources it cites; and every capitalised name must be somewhere in the sources given (or in the
    question). A date or an amount the cited text does not contain, or a name the decision never mentions, is
    not shown.

    Names are looked up in ALL the sources, not only the cited ones, because a decision defines an
    abbreviation once ("Court of Appeals (CA)") and then writes "CA", and an answer may spell it out.
    Whether the cited text really backs the sentence is the checker's job.
    """

    def check(self, sentence: AnswerSentence, sources: dict[str, SourcePassage], question: str = "") -> str | None:
        """Why the sentence cannot be shown, or None if it passes."""
        if not sentence.text.strip():
            return "empty sentence"
        if not sentence.cites:
            return "no source cited"
        missing = [cite for cite in sentence.cites if cite not in sources]
        if missing:
            return f"cites a source that does not exist: {', '.join(missing)}"

        cited = " ".join(sources[cite].text for cite in sentence.cites) + " " + question
        everything = (" ".join(source.text for source in sources.values()) + " " + question).lower()
        for number in _NUMBER.findall(sentence.text):
            if number.rstrip(".,") not in cited:
                return f"number {number} is not in the cited text"
        for name in self._names(sentence.text):
            if name not in _ALWAYS_ALLOWED and name.lower() not in everything:
                return f"name '{name}' is not in the decision"
        return None

    @staticmethod
    def _names(text: str) -> list[str]:
        """Capitalised words that are not simply the first word of a sentence."""
        names: list[str] = []
        for match in _CAPITALISED.finditer(text):
            before = text[: match.start()].rstrip()
            if before == "" or before.endswith((".", "?", "!", ":")):
                continue
            names.append(match.group(0))
        return names
