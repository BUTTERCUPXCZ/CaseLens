"""Separate opinions on older Lawphil pages.

Newer pages print them after an `<hr>` under "SEPARATE CONCURRING OPINION" and the main parser reads those. Older pages (1980s-90s)
print `<p class="cb">Separate Opinion</p>` then a line such as "GUTIERREZ, JR., J., dissenting:" and the opinion, and the main parser
does not read them. This reads that older layout, so a digest can say what each justice who disagreed argued."""
import re
from dataclasses import dataclass

from selectolax.parser import HTMLParser

_LABEL = re.compile(r'<p[^>]*class="cb"[^>]*>\s*Separate Opinion\s*</p>', re.IGNORECASE)
_AUTHOR_LINE = re.compile(r"^(?P<author>[A-ZÑ][A-ZÑ.,\- ']+?),?\s*(?:C\.?\s?J\.?|J\.?|JJ\.?)?(?:,?\s*JR\.?)?\s*,?\s*(?P<kind>concurring|dissenting|separate|concurring and dissenting)\b", re.IGNORECASE)
_END = re.compile(r"^footnotes?$", re.IGNORECASE)


@dataclass(frozen=True)
class SeparateOpinion:
    author: str  # "GUTIERREZ, JR., J."
    kind: str  # "concurring" | "dissenting" | "separate"
    paragraphs: tuple[str, ...]


def parse_separate_opinions(html: str) -> list[SeparateOpinion]:
    opinions: list[SeparateOpinion] = []
    labels = list(_LABEL.finditer(html))
    for position, label in enumerate(labels):
        end = labels[position + 1].start() if position + 1 < len(labels) else len(html)
        # One line per <p>: the author line is split across <b> and <i> tags, so text is joined within a paragraph, not per tag.
        lines = [" ".join(node.text(separator=" ").split()) for node in HTMLParser(html[label.end() : end]).css("p")]
        lines = [line for line in lines if line]
        if not lines:
            continue
        head = _AUTHOR_LINE.match(lines[0].rstrip(":"))
        if head is None and len(lines) > 1:
            head = _AUTHOR_LINE.match(" ".join(lines[:2]).rstrip(":"))
            lines = lines[1:]
        if head is None:
            continue
        body: list[str] = []
        for line in lines[1:]:
            if _END.match(line):
                break  # the opinion's own footnotes
            body.append(line)
        author = re.sub(r"\s*(?:concurring|dissenting|separate)\b.*$", "", lines[0].rstrip(":"), flags=re.IGNORECASE).strip(" ,")
        opinions.append(SeparateOpinion(author, head.group("kind").lower(), tuple(body)))
    return opinions
