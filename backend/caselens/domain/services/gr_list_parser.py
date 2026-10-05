"""Reads a pasted list of G.R. numbers ("88211", "G.R. No. 148263", "88211 (1989)", one per line or separated by commas)."""
import re
from dataclasses import dataclass

from caselens.domain.value_objects import GrNumber

_SPLIT = re.compile(r"[\n;,&]+|\band\b", re.IGNORECASE)
_LABEL = re.compile(r"\bG\.?\s?R\.?\s*(?:Nos?\.?)?\s*:?|\bNos?\.?\s*|#", re.IGNORECASE)
_YEAR = re.compile(r"\(\s*((?:19|20)\d\d)\s*\)")
_MAX_ENTRIES = 5000  # one paste; a month of work is about 2,000


@dataclass(frozen=True)
class ListEntry:
    raw: str  # what the student typed for this entry
    gr_no: GrNumber | None  # None when it is not a G.R. number
    year: int | None = None


class GrListParser:
    def parse(self, text: str) -> list[ListEntry]:
        entries: list[ListEntry] = []
        for piece in _SPLIT.split(text or ""):
            raw = piece.strip()
            if not raw:
                continue
            year_match = _YEAR.search(raw)
            year = int(year_match.group(1)) if year_match else None
            core = _YEAR.sub("", raw)
            core = _LABEL.sub(" ", core).strip(" .:-\t")
            try:
                entries.append(ListEntry(raw, GrNumber(core.replace(" ", "")), year))
            except ValueError:
                entries.append(ListEntry(raw, None, year))
            if len(entries) >= _MAX_ENTRIES:
                break
        return entries
