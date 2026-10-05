from collections.abc import Sequence
from dataclasses import dataclass

from caselens.application.ports.ai import DigestRequest
from caselens.domain.digest import SourcePassage
from caselens.domain.digest_v2 import DigestHeader
from caselens.domain.entities import Case
from caselens.domain.services.case_names import division_name, justice_name, surname_only, short_case_name
from caselens.domain.services.heading_sections import HeadingSections

MAX_PARAGRAPH_CHARS = 2500  # a paragraph longer than this is a quoted statute or a table: the start is enough to cite


@dataclass(frozen=True)
class OpinionText:
    """A separate opinion printed on the decision's page."""

    author: str  # "GUTIERREZ, JR., J."
    kind: str  # "concurring" | "dissenting" | "separate"
    paragraphs: Sequence[str]


def build_digest_request(case: Case, opinions: Sequence[OpinionText], subject: str | None = None, scope: str = "") -> DigestRequest:
    """What the digest writer may use, and nothing else: the decision's numbered paragraphs (P<i>), the Court's caption as the case record
    (C1: the parties, G.R. number, date, division), and each separate opinion's paragraphs (O<n>.<i>) each marked with its author, so
    "Justice Cruz argued ..." can be checked against the passage it cites."""
    paragraphs = case.full_text.split("\n")
    start = HeadingSections.body_start(paragraphs) or 0
    caption = " ".join(line.strip() for line in paragraphs[:start] if line.strip())

    sources: list[SourcePassage] = [SourcePassage("C1", caption)] if caption else []
    sources += [SourcePassage(f"P{i}", paragraphs[i][:MAX_PARAGRAPH_CHARS]) for i in range(start, len(paragraphs)) if paragraphs[i].strip()]
    labels: list[str] = []
    for number, opinion in enumerate(opinions, start=1):
        who = f"{justice_name(opinion.author)}, {opinion.kind}"
        labels.append(f"O{number}: {who}")
        sources += [
            SourcePassage(f"O{number}.{i}", f"({who}) {text[:MAX_PARAGRAPH_CHARS]}") for i, text in enumerate(opinion.paragraphs) if text.strip()
        ]

    ponente = ponente_of(case)
    name = surname_only(short_case_name(case.title))
    when = f", {_long_date(case.decision_date)}" if case.decision_date else ""
    court = f", {division_name(case.division)}" if case.division else ""
    case_line = f"{name}, G.R. No. {case.gr_no}{when}{court}" + (f", ponente {ponente}" if ponente else "")
    return DigestRequest(tuple(sources), case_line, subject, tuple(labels), scope)


def _long_date(day) -> str:
    """ "April 2, 2009", as the client's sample prints dates (no leading zero)."""
    return f"{day:%B} {day.day}, {day.year}"


def ponente_of(case: Case) -> str | None:
    """Who wrote the decision: the stored ponente, or (older pages) the line that ends the caption ("CORTES, J.:")."""
    if case.ponente:
        return justice_name(case.ponente)
    paragraphs = case.full_text.split("\n")
    start = HeadingSections.body_start(paragraphs) or 0
    return justice_name(paragraphs[start - 1].strip().rstrip(":")) if start else None


def build_digest_header(case: Case, subject: str | None) -> DigestHeader:
    when = f", {_long_date(case.decision_date)}" if case.decision_date else ""
    court = f" ({division_name(case.division)})" if case.division else ""
    return DigestHeader(surname_only(short_case_name(case.title)), f"G.R. No. {case.gr_no}{when}{court}", subject, ponente_of(case))
