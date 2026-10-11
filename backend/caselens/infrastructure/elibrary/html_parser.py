"""Parses an SC E-Library decision page (`/thebookshelf/showdocs/1/<id>`) into a domain `Case`.

Page shape (verified on G.R. 193038, 203655 and 211789-90; see tests/fixtures/elibrary/EXPECTED.md):

    ... site menus ...
    755 Phil. 656
    <H2>THIRD DIVISION</H2>
    <H2>[ G.R. No. 193038, March 11, 2015 ]</H2>
    <H3>JOSEFINA V. NOBLEZA, PETITIONER, VS. SHIRLEY B. NUEGA, RESPONDENT.<BR><BR>D E C I S I O N</H3>
    <p><STRONG>VILLARAMA, JR., J.:</STRONG></p>
    <div align="JUSTIFY"> paragraphs split by <br><br>, footnote marks <sup>[1]</sup>, quotes in <blockquote>, lists in tables
      ... SO ORDERED. / the concurring justices / (sometimes) the clerk's NOTICE OF JUDGMENT
      <hr align="LEFT"> <sup>[1]</sup> footnote text <br><br> <sup>[2]</sup> ...
      <hr align="CENTER"> <center><b>CONCURRING OPINION</b></center> <b>CARPIO, J.:</b> ... its own <hr align="LEFT"> footnotes
    <!-- Find it! --> (c) Supreme Court E-Library

Everything from the first <H2> to the footer is read; the menus around it are not.
"""
import re
from dataclasses import dataclass, field
from datetime import date, datetime

from selectolax.parser import HTMLParser

from caselens.application.ports.gateways import CaseParser
from caselens.domain.entities import Case, Footnote, Opinion
from caselens.domain.errors import CaseParseError
from caselens.domain.services.cited_case_extractor import CitedCaseExtractor
from caselens.domain.services.disposition_classifier import DispositionClassifier
from caselens.domain.services.dispositive_extractor import DispositiveExtractor
from caselens.domain.services.gr_label import GrLabelReader
from caselens.domain.services.statute_extractor import StatuteExtractor
from caselens.domain.value_objects import DocType, GrNumber

# One version for all the code that reads decisions: a stored case is re-read when it is lower (`manage reparse`). Bump it in
# lawphil/html_parser.py when either reader's output changes.
from caselens.infrastructure.lawphil.html_parser import PARSER_VERSION

_START = re.compile(r"<h2\b", re.I)
_END = re.compile(r"<!--\s*Find it!|&copy;\s*Supreme Court E-Library|©\s*Supreme Court E-Library", re.I)
_H2 = re.compile(r"<h2\b[^>]*>(.*?)</h2>", re.I | re.S)
_H3 = re.compile(r"<h3\b[^>]*>(.*?)</h3>", re.I | re.S)
_CENTER_RULE = re.compile(r'<hr\b[^>]*align\s*=\s*["\']?center["\']?[^>]*>', re.I)
_LEFT_RULE = re.compile(r'<hr\b[^>]*align\s*=\s*["\']?left["\']?[^>]*>', re.I)
_MARK = re.compile(r"<sup\b[^>]*>\s*\[\s*(\d+)\s*\]\s*</sup>", re.I)
_DROP = re.compile(r"<!--.*?-->|<script\b.*?</script>|<style\b.*?</style>", re.I | re.S)
_BLOCK_TAG = re.compile(r"</?(?:p|div|blockquote|tr|table|tbody|thead|h\d|center|li|ul|ol|hr|br)\b[^>]*>", re.I)
_CELL_TAG = re.compile(r"</?td\b[^>]*>", re.I)
_FOOTNOTE_LINE = re.compile(r"^\[\^(\d+)\]\s*(.*)$", re.S)

_DIVISION = re.compile(r"^(EN BANC|(?:FIRST|SECOND|THIRD|SPECIAL [A-Z]+|SPECIAL) DIVISION)$")
_DATE = re.compile(r"([A-Z][a-z]+\.? \d{1,2}, \d{4})")
_SPACED_TITLE = re.compile(r"^(?:(?:[A-Z] ){3,}[A-Z]|DECISION|RESOLUTION)$")
_AUTHOR = re.compile(r"^(?P<name>[^:]+?),\s*(?:C\.\s?)?J\.\s*:?$")
_RESPONDENTS_END = re.compile(r"Respondents?\.", re.IGNORECASE)
_CERTIFICATION_HEADING = re.compile(r"^(?:C E R T I F I C A T I O N|A T T E S T A T I O N|CERTIFICATION|ATTESTATION)$")
_NOTICE = re.compile(r"^N\s*O\s*T\s*I\s*C\s*E\s+OF\s+J\s*U\s*D\s*G\s*M\s*E\s*N\s*T$", re.I)  # also "N O T I C E OF J U D G M E N T"
_DATE_ONLY = re.compile(r"^[A-Z][a-z]+\.? \d{1,2}, \d{4}$")
_DOC_TYPES = {"DECISION": DocType.DECISION, "RESOLUTION": DocType.RESOLUTION}


@dataclass
class _Section:
    paragraphs: list[str]
    footnotes: list[Footnote] = field(default_factory=list)


class ElibraryCaseParser(CaseParser):
    def __init__(
        self,
        disposition_classifier: DispositionClassifier | None = None,
        dispositive_extractor: DispositiveExtractor | None = None,
        statute_extractor: StatuteExtractor | None = None,
        cited_case_extractor: CitedCaseExtractor | None = None,
    ) -> None:
        self._dispositions = disposition_classifier or DispositionClassifier()
        self._dispositive = dispositive_extractor or DispositiveExtractor()
        self._statutes = statute_extractor or StatuteExtractor()
        self._cited_cases = cited_case_extractor or CitedCaseExtractor()
        self._labels = GrLabelReader()

    def parse(self, html: str, source_url: str) -> Case:
        region = self._region(html)
        header = self._header(region)
        body = region[region.lower().find("</h3>") + len("</h3>"):] if "</h3>" in region.lower() else region
        sections = self._sections(body)
        decision, opinions = sections[0], [o for s in sections[1:] if (o := self._opinion(s))]

        paragraphs = decision.paragraphs
        ponente = None
        if paragraphs and (m := _AUTHOR.match(paragraphs[0])):
            ponente, paragraphs = m.group("name").strip(), paragraphs[1:]
        paragraphs = self._without_notice(paragraphs)
        full_text = "\n".join(paragraphs)
        return Case(
            gr_no=header["gr_no"],
            numbers=header["numbers"],
            source_url=source_url,
            title=header["title"],
            decision_date=header["date"],
            doc_type=header["doc_type"],
            ponente=ponente,
            division=header["division"],
            disposition=self._dispositions.classify(self._dispositive.extract(paragraphs)),
            raw_html=html,
            full_text=full_text,
            parser_version=PARSER_VERSION,
            footnotes=decision.footnotes,
            opinions=opinions,
            statutes=self._statutes.extract(
                "\n".join(self._before_certification(paragraphs)) + "\n" + "\n".join(f.text for f in decision.footnotes)
            ),
            cited_cases=self._cited_cases.extract(full_text, [(f.number, f.text) for f in decision.footnotes]),
        )

    # -- page parts -----------------------------------------------------------------

    @staticmethod
    def _region(html: str) -> str:
        start = _START.search(html)
        if start is None:
            raise CaseParseError("No decision heading found on the E-Library page.")
        end = _END.search(html, start.start())
        return html[start.start(): end.start() if end else len(html)]

    def _header(self, region: str) -> dict:
        headings = [_text(h) for h in _H2.findall(region)]
        gr_line = next((h for h in headings if "G.R." in h.upper()), None)
        if gr_line is None:
            raise CaseParseError("No '[ G.R. No. ..., <date> ]' heading found on the E-Library page.")
        numbers = list(self._labels.read(gr_line.strip("[] "))[0])
        if not numbers:
            raise CaseParseError(f"No G.R. number could be read from {gr_line!r}.")
        found_date = _DATE.search(gr_line)

        title, doc_type = None, DocType.UNKNOWN
        if (h3 := _H3.search(region)) is not None:
            parts = [p for p in (_text(part) for part in re.split(r"<br\s*/?>", h3.group(1), flags=re.I)) if p]
            kind = next((p for p in parts if _SPACED_TITLE.match(p)), None)
            if kind is not None:
                doc_type = _DOC_TYPES.get(kind.replace(" ", ""), DocType.UNKNOWN)
            caption = " ".join(p for p in parts if p != kind)
            for joined in re.findall(r"\[\s*(G\.R\. Nos?\.[^\]]+)\]", caption, flags=re.I):  # the other numbers of a joint decision
                numbers += [n for n in self._labels.read(joined)[0] if n not in numbers]
            title = self._title(caption) or None

        return {
            "gr_no": GrNumber(numbers[0]),
            "numbers": tuple(dict.fromkeys(numbers)),
            "date": _parse_date(found_date.group(1)) if found_date else None,
            "division": next((h for h in headings if _DIVISION.match(h)), None),
            "title": title,
            "doc_type": doc_type,
        }

    def _sections(self, body: str) -> list[_Section]:
        """The decision, then each separate opinion printed after a centred rule under an "...OPINION" heading."""
        chunks = _CENTER_RULE.split(body)
        merged: list[str] = [chunks[0]]
        for chunk in chunks[1:]:
            if self._is_opinion(_blocks(chunk)):
                merged.append(chunk)
            else:
                merged[-1] += chunk  # a centred rule inside the decision (a quote's divider): not a new part
        return [self._section(chunk) for chunk in merged]

    @staticmethod
    def _is_opinion(blocks: list[str]) -> bool:
        return any("OPINION" in b and b.upper() == b for b in blocks[:3])

    def _section(self, html: str) -> _Section:
        rule = _LEFT_RULE.search(html)
        if rule is not None:
            return _Section(_blocks(html[: rule.start()]), self._footnotes(_blocks(html[rule.end():])))
        blocks = _blocks(html)
        start = next((i for i, b in enumerate(blocks) if b.startswith("[^1]") and i > len(blocks) // 2), None)  # no rule: notes begin at [1]
        if start is None:
            return _Section(blocks)
        return _Section(blocks[:start], self._footnotes(blocks[start:]))

    @staticmethod
    def _footnotes(blocks: list[str]) -> list[Footnote]:
        notes: list[Footnote] = []
        for block in blocks:
            match = _FOOTNOTE_LINE.match(block)
            if match:
                notes.append(Footnote(number=int(match.group(1)), anchor=f"fnt{match.group(1)}", text=match.group(2).strip()))
            elif notes:  # a footnote of several paragraphs
                last = notes[-1]
                notes[-1] = Footnote(last.number, last.anchor, f"{last.text} {block}".strip())
        return notes

    def _opinion(self, section: _Section) -> Opinion | None:
        blocks = section.paragraphs
        heading_at = next((i for i, b in enumerate(blocks[:3]) if "OPINION" in b and b.upper() == b), None)
        if heading_at is None:
            return None
        heading, rest = blocks[heading_at], blocks[heading_at + 1:]
        author = None
        if rest and (m := _AUTHOR.match(rest[0])):
            author, rest = m.group("name").strip(), rest[1:]
        return Opinion(kind=_opinion_kind(heading), author=author, text="\n".join(rest), footnotes=section.footnotes)

    @staticmethod
    def _without_notice(paragraphs: list[str]) -> list[str]:
        """The clerk's NOTICE OF JUDGMENT (and the date the office received the decision, just before it) is not the decision."""
        at = next((i for i, p in enumerate(paragraphs) if _NOTICE.match(p)), None)
        if at is None:
            return paragraphs
        if at > 0 and _DATE_ONLY.match(paragraphs[at - 1]):
            at -= 1
        return paragraphs[:at]

    @staticmethod
    def _title(caption: str) -> str:
        first = re.split(r"\[\s*G\.R\.", caption, flags=re.I)[0].strip()  # the first party block of a joint decision
        end = _RESPONDENTS_END.search(first)
        return first[: end.end()] if end else first

    @staticmethod
    def _before_certification(paragraphs: list[str]) -> list[str]:
        """The closing CERTIFICATION ("Pursuant to Section 13, Article VIII of the Constitution ...") is boilerplate, not a citation."""
        for index, paragraph in enumerate(paragraphs):
            if _CERTIFICATION_HEADING.match(paragraph):
                return paragraphs[:index]
        return paragraphs


_PHIL_REPORTS = re.compile(r"\b(\d{1,4}\s+Phil\.\s+\d{1,5})\b")


def philippine_reports_citation(html: str | None) -> str | None:
    """The Philippine Reports citation an E-Library page prints above the division ("755 Phil. 656"), or None."""
    if not html:
        return None
    start = _START.search(html)
    head = html[max(0, (start.start() if start else 0) - 600): start.start() if start else 0]
    found = _PHIL_REPORTS.search(_text(head)) if head else None
    return " ".join(found.group(1).split()) if found else None


def _blocks(html: str) -> list[str]:
    """The text of an HTML fragment as paragraphs: one per block element or line break; table cells of a row on one line;
    footnote marks kept as [^N] (as the Lawphil reader does)."""
    html = _DROP.sub("", html)
    html = _MARK.sub(r"[^\1]", html)
    html = _BLOCK_TAG.sub("\n", html)
    html = _CELL_TAG.sub(" ", html)
    text = HTMLParser(f"<div>{html}</div>").text(separator="")
    return [line for line in (" ".join(raw.split()) for raw in text.split("\n")) if line]


def _text(fragment: str) -> str:
    return " ".join(HTMLParser(f"<div>{_DROP.sub('', fragment)}</div>").text(separator=" ").split())


def _opinion_kind(heading: str) -> str:
    heading = heading.upper()
    if "DISSENT" in heading and "CONCUR" in heading:
        return "concurring_dissenting"
    if "DISSENT" in heading:
        return "dissenting"
    if "CONCUR" in heading:
        return "concurring"
    return "separate"


def _parse_date(text: str) -> date | None:
    text = text.replace(".", "")
    for fmt in ("%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None
