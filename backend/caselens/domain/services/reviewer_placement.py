import re
from dataclasses import dataclass, field

_ZERO_WIDTH = dict.fromkeys(map(ord, "​‌‍﻿"), None)


def normalise(text: str) -> str:
    """Text as compared when looking for a citation: no zero-width marks, one space between words, lower case."""
    return re.sub(r"\s+", " ", text.translate(_ZERO_WIDTH).replace(" ", " ")).strip().lower()


# The label lines of the student's own digest boxes ("Facts", "Issue:", "Doctrine"...). A citation line followed by one of
# these is the header of a digest the student already wrote, not a place where the case is cited in the reviewer's text.
_OWN_DIGEST_LABELS = ("facts", "issue", "issues", "ruling", "doctrine", "topic explained", "why this case matters")


@dataclass(frozen=True)
class CitationRef:
    citation_id: int
    raw: str  # the citation as the student wrote it, e.g. "GR no 180046"
    case_id: int | None  # the stored decision it was matched to (None: not found, nothing to digest)


@dataclass
class Placement:
    after_block: dict[int, list[int]] = field(default_factory=dict)  # block index -> citation ids whose box goes right after it
    unplaced: list[int] = field(default_factory=list)  # a matched citation whose text could not be found in any block


class CitationPlacer:
    """Decides where each digest box goes in the student's reviewer: right after the first paragraph that cites the case.

    One box per case (a case cited five times gets one, at its first citation). A citation that matched no
    decision gets no box. A line that is only the header of a digest the student already wrote (the citation, then
    "Facts" or "Doctrine" on the next line) does not count as a place the case is cited, so a reviewer that is
    already digested gets the new box at the end instead of in the middle of the student's own boxes. A citation whose text cannot be found in any paragraph (it sits in a table or a text
    box, say) is reported as unplaced so the box can go at the end rather than being lost.
    """

    def place(self, blocks: list[str], refs: list[CitationRef]) -> Placement:
        normalised = [normalise(block) for block in blocks]
        placement = Placement()
        done: set[int] = set()
        for ref in refs:
            if ref.case_id is None or ref.case_id in done:
                continue
            done.add(ref.case_id)
            needle = normalise(ref.raw)
            index = next(
                (i for i, text in enumerate(normalised) if needle and needle in text and not self._is_own_digest_header(normalised, i)),
                None,
            )
            if index is None:
                placement.unplaced.append(ref.citation_id)
            else:
                placement.after_block.setdefault(index, []).append(ref.citation_id)
        return placement

    @staticmethod
    def _is_own_digest_header(blocks: list[str], index: int) -> bool:
        following = blocks[index + 1] if index + 1 < len(blocks) else ""
        label = following.rstrip(" :")
        return label in _OWN_DIGEST_LABELS or any(following.startswith(f"{name}:") for name in _OWN_DIGEST_LABELS)
