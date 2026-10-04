import re

_PART = re.compile(r"^(part|chapter|book|title)\b", re.IGNORECASE)
_ROMAN = re.compile(r"^[IVXLCDM]+\.\s+\S")  # "I. Legislative power"
_LETTER_OR_NUMBER = re.compile(r"^(?:[A-Z]|\d{1,2})\.\s+[A-Z]")  # "A. General Plenary powers", "2. Reclassification"
_DIGEST = re.compile(r"^digest\s+\d+\s*:", re.IGNORECASE)  # the student's own "Digest 1: Facts and Doctrine"
_MAX_CHARS = 110


class ReviewerHeadings:
    """Which paragraphs of a reviewer are headings, so the document can be read by its structure.

    Plain text only, no guessing about meaning: a heading is a short line that is not a sentence (it does not end in a
    full stop or semicolon) and looks like one: the title on the first line, "PART NINE: ...", "I. Legislative power",
    "A. General Plenary powers", a line in capitals, or a short label ending in a colon. Returns 1 (title), 2 or 3.
    """

    def level(self, text: str, position: int) -> int | None:
        line = text.strip()
        words = line.split()
        if not line or len(line) > _MAX_CHARS or len(words) > 14 or line.endswith((".", ";", ",")):
            return None
        letters = [c for c in line if c.isalpha()]
        if position == 0 and len(words) <= 8:
            return 1
        if _PART.match(line) or (len(letters) >= 4 and line.upper() == line and len(words) <= 12):
            return 1
        if _ROMAN.match(line):
            return 2
        if _LETTER_OR_NUMBER.match(line) or _DIGEST.match(line) or (line.endswith(":") and len(words) <= 8):
            return 3
        return None

    def own_digest_count(self, blocks: list[str]) -> int:
        """How many digests the student already wrote inside the file ("Digest 1: Facts and Doctrine", "Digest 2: ...").
        The app cannot tell their boxes from the reviewer's own text, so it only counts them and says so."""
        return sum(1 for block in blocks if _DIGEST.match(block.strip()))
