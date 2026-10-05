from caselens.domain.case_digest import (
    STANDARD_QUESTIONS,
    TOPIC_KEY,
    WHY_KEY,
    DigestField,
    DigestTemplate,
    FieldKind,
    FieldOrigin,
    FieldState,
    Passage,
)
from caselens.domain.digest import ParagraphRange, SectionKind
from caselens.domain.services.heading_sections import HeadingSections
from caselens.domain.services.passage_suggester import IssueFinder
from caselens.domain.services.ruling_locator import RulingLocator

MAX_SHOWN_PARAGRAPHS = 4  # a Court section can be 50 paragraphs long (a quoted executive order, say)
_CUSTOM_LABEL_CHARS = 120
_PICK_OR_PASTE = "Pick the paragraphs you want, or paste them."
_MISSING = {
    "facts": ("Facts", f"The Court did not label the facts in this decision. {_PICK_OR_PASTE}"),
    "doctrine": ("Doctrine", "Pick the paragraph that states the rule, or paste it. We do not guess which one it is."),
    "issues": ("Issue", f"The Court did not label the issue in this decision. {_PICK_OR_PASTE}"),
}
_NOT_FOUND = {
    "doctrine": "We did not find one paragraph where the Court states the rule. Pick it, or paste it.",
    "issues": f"We did not find where the Court states the issue in this decision. {_PICK_OR_PASTE}",
    "facts": f"We did not find the Court's account of the facts. {_PICK_OR_PASTE}",
}


class DigestFieldFactory:
    """Builds the fields of a new digest from a stored decision. Everything here is rules on the Court's own
    text and costs nothing: Facts and Issue only when the Court labelled them, the Ruling always, the Doctrine
    left for the student. The AI answers are only placeholders (pending) until the worker writes them.
    """

    def __init__(
        self,
        sections: HeadingSections | None = None,
        rulings: RulingLocator | None = None,
        issues: IssueFinder | None = None,
        look_for_passages: bool = False,
    ) -> None:
        self._sections = sections or HeadingSections()
        self._rulings = rulings or RulingLocator()
        self._issues = issues or IssueFinder()
        # True when an AI that only points at paragraphs will look for the Facts, Issue and Doctrine the rules could not
        # find: those fields start as "pending" instead of "empty".
        self._look = look_for_passages

    def build(self, template: DigestTemplate, full_text: str, questions: list[str] | None = None) -> list[DigestField]:
        paragraphs = full_text.split("\n")
        found = self._sections.find(paragraphs)
        ruling = self._rulings.locate(paragraphs)

        body_start = self._sections.body_start(paragraphs)
        facts = self._court_section("facts", "Facts", found.get(SectionKind.FACTS), paragraphs, "The Court did not label the facts in this decision.")
        doctrine = self.missing("doctrine", pending=self._look)
        fields = [facts, doctrine] if template is DigestTemplate.FACTS_AND_DOCTRINE else [
            facts,
            self._issue(found.get(SectionKind.ISSUES), paragraphs, body_start, ruling),
            self._ruling(ruling, paragraphs),
            doctrine,
            self._answer(TOPIC_KEY),
            self._answer(WHY_KEY),
        ]
        for number, question in enumerate(questions or [], start=1):
            fields.append(self.custom_question(f"q{number}", question))
        return fields

    def pickable_range(self, full_text: str) -> tuple[int, int] | None:
        """The paragraphs a student may pick from: the decision's body, up to the end of the final ruling."""
        paragraphs = full_text.split("\n")
        start, ruling = self._sections.body_start(paragraphs), self._rulings.locate(paragraphs)
        return None if start is None or ruling is None else (start, ruling.last)

    @staticmethod
    def custom_question(key: str, question: str) -> DigestField:
        label = question if len(question) <= _CUSTOM_LABEL_CHARS else question[: _CUSTOM_LABEL_CHARS - 1] + "…"
        return DigestField(key, label, FieldKind.ANSWER, state=FieldState.PENDING, question=question)

    @staticmethod
    def verbatim_text(paragraphs: list[str], rng: ParagraphRange) -> tuple[str, Passage, str | None]:
        """The Court's paragraphs for a range, cut to MAX_SHOWN_PARAGRAPHS (with a plain note when cut)."""
        last = min(rng.last, rng.first + MAX_SHOWN_PARAGRAPHS - 1)
        text = "\n\n".join(paragraphs[i] for i in range(rng.first, last + 1))
        note = None
        if last < rng.last:
            note = f"Showing the first {MAX_SHOWN_PARAGRAPHS} of {len(rng)} paragraphs. Pick the passage you want."
        return text, Passage(rng.first, last), note

    def _issue(self, labelled: ParagraphRange | None, paragraphs: list[str], body_start: int | None, ruling: ParagraphRange | None) -> DigestField:
        """The Issue: under the Court's own heading (cut back to the statement and its questions), else the Court's own
        cue words, else missing."""
        if labelled is not None:
            return self._court_section("issues", "Issue", self._issues.cap(paragraphs, labelled), paragraphs, "")
        found = self._issues.find(paragraphs, body_start, ruling.first if ruling else None)
        if found is not None:
            return self.suggested("issues", "Issue", found.range, paragraphs, found.reason)
        return self.missing("issues", pending=self._look)

    @staticmethod
    def suggested(key: str, label: str, rng: ParagraphRange, paragraphs: list[str], reason: str) -> DigestField:
        """The Court's own paragraphs, found for the student (by rules, or pointed at by an AI): shown as a suggestion to check."""
        text, passage, note = DigestFieldFactory.verbatim_text(paragraphs, rng)
        return DigestField(key, label, FieldKind.VERBATIM, text, FieldOrigin.COURT_SUGGESTED, passage=passage, note=note, reason=reason)

    @staticmethod
    def missing(key: str, *, pending: bool = False, searched: bool = False) -> DigestField:
        """A Court field with nothing in it. `pending`: a passage is being looked for. `searched`: it was, and none was found."""
        label, note = _MISSING[key]
        if pending:
            return DigestField(key, label, FieldKind.VERBATIM, state=FieldState.PENDING)
        return DigestField(key, label, FieldKind.VERBATIM, note=_NOT_FOUND[key] if searched else note)

    def _court_section(self, key: str, label: str, rng: ParagraphRange | None, paragraphs: list[str], missing: str) -> DigestField:
        if rng is None:
            return DigestField(key, label, FieldKind.VERBATIM, state=FieldState.PENDING if self._look else FieldState.READY, note=None if self._look else f"{missing} Pick the paragraphs you want, or paste them.")
        text, passage, note = self.verbatim_text(paragraphs, rng)
        return DigestField(key, label, FieldKind.VERBATIM, text, FieldOrigin.COURT_HEADING, passage=passage, note=note)

    def _ruling(self, rng: ParagraphRange | None, paragraphs: list[str]) -> DigestField:
        if rng is None:
            return DigestField("ruling", "Ruling", FieldKind.VERBATIM, note="We could not find the Court's final ruling. Pick it or paste it.")
        text, passage, note = self.verbatim_text(paragraphs, rng)
        return DigestField("ruling", "Ruling", FieldKind.VERBATIM, text, FieldOrigin.COURT_RULING, passage=passage, note=note)

    @staticmethod
    def _answer(key: str) -> DigestField:
        label, question = STANDARD_QUESTIONS[key]
        return DigestField(key, label, FieldKind.ANSWER, state=FieldState.PENDING, question=question)
