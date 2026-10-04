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
from caselens.domain.services.ruling_locator import RulingLocator

MAX_SHOWN_PARAGRAPHS = 4  # a Court section can be 50 paragraphs long (a quoted executive order, say)
_CUSTOM_LABEL_CHARS = 120


class DigestFieldFactory:
    """Builds the fields of a new digest from a stored decision. Everything here is rules on the Court's own
    text and costs nothing: Facts and Issue only when the Court labelled them, the Ruling always, the Doctrine
    left for the student. The AI answers are only placeholders (pending) until the worker writes them.
    """

    def __init__(self, sections: HeadingSections | None = None, rulings: RulingLocator | None = None) -> None:
        self._sections = sections or HeadingSections()
        self._rulings = rulings or RulingLocator()

    def build(self, template: DigestTemplate, full_text: str, questions: list[str] | None = None) -> list[DigestField]:
        paragraphs = full_text.split("\n")
        found = self._sections.find(paragraphs)
        ruling = self._rulings.locate(paragraphs)

        facts = self._court_section("facts", "Facts", found.get(SectionKind.FACTS), paragraphs, "The Court did not label the facts in this decision.")
        doctrine = DigestField(
            "doctrine", "Doctrine", FieldKind.VERBATIM,
            note="Pick the paragraph that states the rule, or paste it. We do not guess which one it is.",
        )
        fields = [facts, doctrine] if template is DigestTemplate.FACTS_AND_DOCTRINE else [
            facts,
            self._court_section("issues", "Issue", found.get(SectionKind.ISSUES), paragraphs, "The Court did not label the issue in this decision."),
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

    def _court_section(self, key: str, label: str, rng: ParagraphRange | None, paragraphs: list[str], missing: str) -> DigestField:
        if rng is None:
            return DigestField(key, label, FieldKind.VERBATIM, note=f"{missing} Pick the paragraphs you want, or paste them.")
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
