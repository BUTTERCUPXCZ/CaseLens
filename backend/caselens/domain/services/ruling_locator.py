import re

from caselens.domain.digest import ParagraphRange

_SO_ORDERED = re.compile(r"^(?:IT IS )?SO ORDERED\b", re.IGNORECASE)
# The dispositive paragraph opens in capitals. A quoted lower-court ruling, or a sentence that merely
# starts with "Accordingly,", must not be taken for it, so the capitals are required first.
_OPENER = re.compile(
    r"^(?:WHEREFORE|ACCORDINGLY|IN VIEW|FOR THESE REASONS|FOR THE FOREGOING REASONS|IN LIGHT|THEREFORE|PREMISES CONSIDERED)\b"
)
_LOOSE_OPENER = re.compile(
    r"^(?:WHEREFORE|ACCORDINGLY|IN VIEW|FOR THESE REASONS|FOR THE FOREGOING REASONS|IN LIGHT|THEREFORE)\b", re.IGNORECASE
)
_WINDOW = 8  # a ruling can run over several paragraphs (costs, remand, directions)


class RulingLocator:
    """Finds the Court's own final ruling: the paragraphs from its opening word (`WHEREFORE ...`) up to the
    last `SO ORDERED`.

    Anchoring on the LAST `SO ORDERED` matters: a decision often quotes the trial court's and the Court of
    Appeals' `WHEREFORE ... SO ORDERED` earlier on, and the final ruling can open with `ACCORDINGLY` or
    `IN VIEW OF THE FOREGOING` instead.
    """

    def final_order_index(self, paragraphs: list[str]) -> int | None:
        return next((i for i in range(len(paragraphs) - 1, -1, -1) if _SO_ORDERED.match(paragraphs[i])), None)

    def locate(self, paragraphs: list[str]) -> ParagraphRange | None:
        end = self.final_order_index(paragraphs)
        if end is None:
            return self._without_closing_order(paragraphs)
        window = range(end - 1, max(end - 1 - _WINDOW, -1), -1)
        for pattern in (_OPENER, _LOOSE_OPENER):
            start = next((i for i in window if pattern.match(paragraphs[i])), None)
            if start is not None:
                return ParagraphRange(start, end - 1)
        return None

    @staticmethod
    def _without_closing_order(paragraphs: list[str]) -> ParagraphRange | None:
        start = next((i for i in range(len(paragraphs) - 1, -1, -1) if _OPENER.match(paragraphs[i])), None)
        if start is None:
            return None
        return ParagraphRange(start, min(start + _WINDOW - 1, len(paragraphs) - 1))
