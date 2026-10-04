"""Parses a Lawphil case page into a domain `Case`.

Page shape (verified on GR 180046, see tests/fixtures/EXPECTED.md):

    <header table> <blockquote>
      centered court / division / "G.R. No. N  <date>" / party block / "D E C I S I O N" / "PONENTE, J.:"
      ... body paragraphs, footnote markers  <a name="rnt5"><sup>5</sup></a> ...
      <p><b>Footnotes</b></p> <dir><p><a name="fnt5">...</a> note text</p>...</dir>
      <a class="id">The Lawphil Project - Arellano Law Foundation</a>
    <hr> "SEPARATE CONCURRING OPINION" / "BRION, J.:" / body / Footnotes (fnt1b ...) / footer

Everything before the first footer is the decision; each later section that starts
with an "...OPINION" heading is an opinion printed on the same page.
"""
import re
from dataclasses import dataclass
from datetime import date, datetime

from selectolax.parser import HTMLParser

from caselens.application.ports.gateways import CaseParser
from caselens.domain.entities import Case, Footnote, Opinion
from caselens.domain.errors import CaseParseError
from caselens.domain.services.cited_case_extractor import CitedCaseExtractor
from caselens.domain.services.disposition_classifier import DispositionClassifier
from caselens.domain.services.gr_label import GrLabelReader
from caselens.domain.services.dispositive_extractor import DispositiveExtractor
from caselens.domain.services.statute_extractor import StatuteExtractor
from caselens.domain.services.text_normalizer import LawphilWatermarkRule
from caselens.domain.value_objects import DocType, GrNumber

# Bump whenever the parser's OUTPUT changes, so `manage reparse` knows which stored cases are stale.
# 2: reads the justices' signature table; empty footnotes kept; multi-paragraph rulings
# 3: certification boilerplate no longer counted as a cited statute; "(R.A.)" statutes; "Citing" / "et al." titles
# 4: every G.R. number of a joint decision (extra numbers sit on their own caption lines)
# 5: the layout used from about 2016 (bracketed "[ G.R. No. N. date ]" header, `<a class="nt">` footnotes)
# 6: the ruling is the paragraphs before the LAST "SO ORDERED" (a quoted lower-court WHEREFORE no longer wins)
PARSER_VERSION = 6

_SECTION_FOOTER = re.compile(r'<a class="id">\s*The Lawphil Project[^<]*</a>', re.I)
_MARKER = re.compile(r'<a name="rnt(\d+)b?"[^>]*>\s*<sup>\s*\d+\s*</sup>\s*</a>', re.I)
# Newer pages mark a footnote in the text with a bare `<a class="nt">3</a>` (no anchor name, no <sup>).
_NEW_MARKER = re.compile(r'<a class="nt">\s*(\d+)\s*</a>', re.I)
_FOOTNOTE_ANCHOR = re.compile(r'<a name="(fnt(\d+)b?)"[^>]*>.*?</a>', re.I | re.S)
_NEW_FOOTNOTE_ANCHOR = re.compile(r'<a class="nt">\s*(\d+)\s*</a>', re.I)
_BR = re.compile(r"<br\s*/?>", re.I)

_DIVISION = re.compile(r"^(EN BANC|(?:FIRST|SECOND|THIRD|SPECIAL [A-Z]+) DIVISION)$")
_GR_LINE = re.compile(
    r"^(?:\[\s*)?G\.R\. Nos?\.?\s*(?P<num>L-?\d{3,6}|\d{3,7})\b.*?(?P<date>[A-Z][a-z]+\.? \d{1,2}, \d{4})?\s*\]?$"
)
# "D E C I S I O N" (older pages, also "R E S O L U T I O N") or plain "DECISION" / "RESOLUTION" (newer pages)
_SPACED_TITLE = re.compile(r"^(?:(?:[A-Z] ){3,}[A-Z]|DECISION|RESOLUTION)$")
_AUTHOR = re.compile(r"^(?P<name>.+?),\s*(?:C\.\s?)?J\.\s*:?$")
_RESPONDENTS_END = re.compile(r"Respondents?\.", re.IGNORECASE)
_CAPTION_NUMBER_LINE = re.compile(r"^G\.R\. Nos?\.", re.IGNORECASE)
_CERTIFICATION_HEADING = re.compile(r"^(?:C E R T I F I C A T I O N|A T T E S T A T I O N)$")

_DOC_TYPES = {"DECISION": DocType.DECISION, "RESOLUTION": DocType.RESOLUTION}


@dataclass
class _Section:
    paragraphs: list[str]
    footnotes: list[Footnote]


class LawphilCaseParser(CaseParser):
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
        self._watermark = LawphilWatermarkRule()
        self._labels = GrLabelReader()

    def parse(self, html: str, source_url: str) -> Case:
        fragments = _SECTION_FOOTER.split(html)
        decision = self._read_section(fragments[0])
        opinions = [
            opinion
            for fragment in fragments[1:]
            if (opinion := self._read_opinion(self._read_section(fragment)))
        ]

        header = self._parse_header(decision.paragraphs)
        full_text = "\n".join(decision.paragraphs)
        footnote_texts = [f.text for f in decision.footnotes]
        numbered_footnotes = [(f.number, f.text) for f in decision.footnotes]

        return Case(
            gr_no=header["gr_no"],
            numbers=header["numbers"],
            source_url=source_url,
            title=header["title"],
            decision_date=header["date"],
            doc_type=header["doc_type"],
            ponente=header["ponente"],
            division=header["division"],
            disposition=self._dispositions.classify(self._dispositive.extract(decision.paragraphs)),
            raw_html=html,
            full_text=full_text,
            parser_version=PARSER_VERSION,
            footnotes=decision.footnotes,
            opinions=opinions,
            statutes=self._statutes.extract(
                "\n".join(self._before_certification(decision.paragraphs))
                + "\n"
                + "\n".join(footnote_texts)
            ),
            cited_cases=self._cited_cases.extract(full_text, numbered_footnotes),
        )

    # -- sections -----------------------------------------------------------------

    def _read_section(self, fragment: str) -> _Section:
        html = self._watermark.apply(fragment)
        html = _BR.sub(" ", html)
        html = _MARKER.sub(r"[^\1]", html)  # keep footnote markers visible as [^N]
        html = self._mark_new_style_footnotes(html)

        paragraphs: list[str] = []
        footnotes: list[Footnote] = []
        in_footnotes = False

        # traverse() walks in document order; css("p, td") would list all <p> first and
        # all <td> after, putting the signature cells behind the "Footnotes" heading.
        for node in HTMLParser(html).root.traverse():
            if node.tag not in ("p", "td"):
                continue
            # The justices' signature block is a <table>; its leaf cells hold text just
            # like paragraphs. Layout cells that merely wrap other content are skipped.
            # (css() includes the node itself, so a leaf cell matches exactly once.)
            if node.tag == "td" and len(node.css("p, td, table")) > 1:
                continue
            text = self._clean(node.text(separator=""))
            if text == "Footnotes":
                in_footnotes = True
            elif in_footnotes:
                # Keep a footnote even when its text is empty: Lawphil's own page has
                # an empty `fnt6` for GR 173931, and the marker in the text points at it.
                footnote = self._footnote(node.html)
                if footnote:
                    footnotes.append(footnote)
            elif text:
                paragraphs.append(text)
        return _Section(paragraphs, footnotes)

    @staticmethod
    def _mark_new_style_footnotes(html: str) -> str:
        """Body markers become `[^N]` as above. In the newer layout the footnote list uses the same
        `<a class="nt">N</a>` tag, so the list's own number is left for `_footnote` to read."""
        head, sep, tail = html.partition("Footnotes</p>")
        return _NEW_MARKER.sub(r"[^\1]", head) + sep + tail

    def _footnote(self, paragraph_html: str) -> Footnote | None:
        anchor = _FOOTNOTE_ANCHOR.search(paragraph_html)
        if not anchor:
            return self._new_style_footnote(paragraph_html)
        body = _FOOTNOTE_ANCHOR.sub("", paragraph_html, count=1)
        text = self._clean(HTMLParser(body).text(separator=""))
        return Footnote(number=int(anchor.group(2)), anchor=anchor.group(1), text=text)

    def _new_style_footnote(self, paragraph_html: str) -> Footnote | None:
        """`<p class="jn"><a class="nt">1</a> <i>Rollo,</i> pp. 47-58 ...</p>`. The page has no anchor
        to link to, so the anchor name is the one the older layout would have used."""
        match = _NEW_FOOTNOTE_ANCHOR.search(paragraph_html)
        if not match:
            return None
        body = _NEW_FOOTNOTE_ANCHOR.sub("", paragraph_html, count=1)
        text = self._clean(HTMLParser(body).text(separator=""))
        return Footnote(number=int(match.group(1)), anchor=f"fnt{match.group(1)}", text=text)

    def _read_opinion(self, section: _Section) -> Opinion | None:
        if not section.paragraphs or "OPINION" not in section.paragraphs[0]:
            return None
        heading, rest = section.paragraphs[0], section.paragraphs[1:]
        author = None
        if rest and (m := _AUTHOR.match(rest[0])):
            author, rest = m.group("name"), rest[1:]
        return Opinion(
            kind=self._opinion_kind(heading),
            author=author,
            text="\n".join(rest),
            footnotes=section.footnotes,
        )

    @staticmethod
    def _opinion_kind(heading: str) -> str:
        heading = heading.upper()
        if "DISSENT" in heading and "CONCUR" in heading:
            return "concurring_dissenting"
        if "DISSENT" in heading:
            return "dissenting"
        if "CONCUR" in heading:
            return "concurring"
        return "separate"

    # -- header -------------------------------------------------------------------

    def _parse_header(self, paragraphs: list[str]) -> dict:
        gr_index, gr_match = next(
            ((i, m) for i, p in enumerate(paragraphs[:15]) if (m := _GR_LINE.match(p))),
            (None, None),
        )
        if gr_match is None:
            raise CaseParseError("No 'G.R. No. ... <date>' line found in the page header.")

        head = paragraphs[:25]
        title_index = gr_index + 1
        doc_type_index = next((i for i, p in enumerate(head) if _SPACED_TITLE.match(p)), None)
        caption = head[gr_index : doc_type_index if doc_type_index is not None else 15]
        doc_type = DocType.UNKNOWN
        ponente = None
        if doc_type_index is not None:
            doc_type = _DOC_TYPES.get(head[doc_type_index].replace(" ", ""), DocType.UNKNOWN)
            if doc_type_index + 1 < len(paragraphs) and (
                m := _AUTHOR.match(paragraphs[doc_type_index + 1])
            ):
                ponente = m.group("name")

        return {
            "gr_no": GrNumber(gr_match.group("num")),
            "numbers": self._numbers(caption, gr_match.group("num")),
            "date": self._parse_date(gr_match.group("date")),
            "division": next((p for p in head if _DIVISION.match(p)), None),
            "title": self._title(paragraphs[title_index]) if title_index < len(paragraphs) else None,
            "doc_type": doc_type,
            "ponente": ponente,
        }

    def _numbers(self, caption: list[str], first: str) -> tuple[str, ...]:
        """Every G.R. number printed in the caption. A joint decision prints the first beside
        the date and the others on their own lines after the first party block:
        `G.R. No. 211972 July 22, 2015` ... `G.R. No. 212045`."""
        found = [GrNumber(first).value]
        for line in caption:
            if _CAPTION_NUMBER_LINE.match(line):
                for number in self._labels.read(line)[0]:
                    if number not in found:
                        found.append(number)
        return tuple(found)

    @staticmethod
    def _title(party_block: str) -> str:
        end = _RESPONDENTS_END.search(party_block)
        return party_block[: end.end()] if end else party_block

    @staticmethod
    def _before_certification(paragraphs: list[str]) -> list[str]:
        """Every decision ends with the same CERTIFICATION ("Pursuant to Section 13,
        Article VIII of the Constitution, I certify ..."). That is boilerplate, not a
        citation, so it must not count as the decision relying on that provision."""
        for index, paragraph in enumerate(paragraphs):
            if _CERTIFICATION_HEADING.match(paragraph):
                return paragraphs[:index]
        return paragraphs

    @staticmethod
    def _parse_date(text: str | None) -> date | None:
        if not text:
            return None
        text = text.replace(".", "")
        for fmt in ("%B %d, %Y", "%b %d, %Y"):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
        return None

    @staticmethod
    def _clean(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()
