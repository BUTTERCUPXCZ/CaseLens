import re
from dataclasses import dataclass

from caselens.domain.value_objects import GrNumber

_GR_LABEL = re.compile(r"^\s*g\.?\s?r\.?\s*(?:nos?\.?)?\s*", re.IGNORECASE)
_NUMBER = re.compile(r"^(?:L-?\d{3,6}|\d{3,7})$", re.IGNORECASE)
_NOISE = {"vs", "v", "versus", "et", "al", "the", "of", "and"}


@dataclass(frozen=True)
class CatalogQuery:
    """What a student typed: either (the start of) a G.R. number, or words from a case name."""

    number: str | None  # normalised "180046" / "L-12345": matched against G.R. numbers
    words: tuple[str, ...]  # matched against the case name

    @property
    def is_empty(self) -> bool:
        return self.number is None and not self.words


class CatalogQueryParser:
    def parse(self, text: str) -> CatalogQuery:
        cleaned = " ".join(text.split())
        if not cleaned:
            return CatalogQuery(None, ())

        bare = _GR_LABEL.sub("", cleaned).strip()
        if _NUMBER.match(bare):
            return CatalogQuery(GrNumber(bare).value, ())

        words = tuple(
            w for w in re.findall(r"[\w'\u2019.-]+", cleaned.lower()) if w.strip(".-") and w not in _NOISE
        )
        return CatalogQuery(None, words)
