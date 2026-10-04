import re

from caselens.domain.entities import Statute
from caselens.domain.value_objects import StatuteType

_NO = r"(?:No\.?\s*)?"
# Decisions write "Republic Act (R.A.) No. 7722": the abbreviation may follow the full name.
_RA_ABBR = r"(?:\(R\.A\.\)\s*)?"
_EO_ABBR = r"(?:\(E\.O\.\)\s*)?"
_PATTERNS: list[tuple[StatuteType, re.Pattern[str]]] = [
    (StatuteType.REPUBLIC_ACT, re.compile(rf"\b(?:Republic Act\s*{_RA_ABBR}{_NO}|R\.A\.\s*{_NO}|RA\s+{_NO})(\d{{1,5}})\b")),
    (StatuteType.EXECUTIVE_ORDER, re.compile(rf"\b(?:Executive Order\s*{_EO_ABBR}{_NO}|E\.O\.\s*{_NO}|EO\s+{_NO})(\d{{1,5}})\b")),
    (StatuteType.BATAS_PAMBANSA, re.compile(rf"\b(?:Batas Pambansa\s*(?:Blg\.?|Bilang|{_NO})\s*|B\.P\.\s*(?:Blg\.?\s*)?|BP\s+(?:Blg\.?\s*)?)(\d{{1,4}})\b")),
    (StatuteType.COMMONWEALTH_ACT, re.compile(rf"\bCommonwealth Act\s*{_NO}(\d{{1,4}})\b")),
]
_CONST_SECTION_ARTICLE = re.compile(r"\bSection\s+(\d+[A-Za-z]?),\s+Article\s+([IVXLC]+)\b")
_CONST_ARTICLE_SECTION = re.compile(r"\bArticle\s+([IVXLC]+),\s+Section\s+(\d+[A-Za-z]?)\b")


class StatuteExtractor:
    """Finds statutes and Constitution provisions cited in a block of text.

    Results are de-duplicated by (type, number) and keep the order of first appearance.
    "Section X, Article Y" is treated as a Constitution reference, which is how
    Philippine decisions cite it.
    """

    def extract(self, text: str) -> list[Statute]:
        hits: list[tuple[int, Statute]] = []

        for statute_type, pattern in _PATTERNS:
            for m in pattern.finditer(text):
                hits.append((m.start(), Statute(statute_type, m.group(1), m.group(0).strip())))

        for m in _CONST_SECTION_ARTICLE.finditer(text):
            hits.append((m.start(), self._constitution(m.group(2), m.group(1), m.group(0))))
        for m in _CONST_ARTICLE_SECTION.finditer(text):
            hits.append((m.start(), self._constitution(m.group(1), m.group(2), m.group(0))))

        unique: dict[tuple[StatuteType, str], Statute] = {}
        for _, statute in sorted(hits, key=lambda h: h[0]):
            unique.setdefault((statute.statute_type, statute.number), statute)
        return list(unique.values())

    @staticmethod
    def _constitution(article: str, section: str, raw: str) -> Statute:
        return Statute(StatuteType.CONSTITUTION, f"Art. {article}, Sec. {section}", raw.strip())
