"""Turns a decision's plain text (one paragraph per line, footnote markers as `[^12]`) into styled blocks.

This is the Python twin of `frontend/src/features/cases/readerBlocks.ts`: the same simple rules, so a downloaded
Word file reads like the page on screen. Nothing is added, removed or reworded; each non-empty line becomes one
block and only its style differs."""
import re
from dataclasses import dataclass
from enum import Enum

_SPACED_TITLE = re.compile(r"^(?:[A-Z] ){3,}[A-Z]$")  # "D E C I S I O N"
_PONENTE = re.compile(r", (?:C\.)?J\.:?$")
_NOTICE = re.compile(r"^(?:C E R T I F I C A T I O N|A T T E S T A T I O N)$")
_SIGNATURE = re.compile(r"\b(?:Associate|Chief) Justice\b")
_WE_CONCUR = re.compile(r"^WE CONCUR", re.IGNORECASE)
_END_PUNCTUATION = re.compile(r"[.:;,)\"”’]$")
_NOT_A_HEADING = re.compile(r"^(?:\(Sgd\.\)|x x x|SO ORDERED|WE CONCUR|By the President)", re.IGNORECASE)
_STARTS_LIKE_HEADING = re.compile(r"^[A-Z0-9]")
_MARKER = re.compile(r"\[\^(\d+)\]")
_MIN_FOLLOWING_LINE = 30


class BlockKind(str, Enum):
    CAPTION = "caption"
    PARTIES = "parties"
    TITLE = "title"
    PONENTE = "ponente"
    HEADING = "heading"
    SIGNATURE = "signature"
    NOTICE = "notice"
    PARAGRAPH = "paragraph"


@dataclass(frozen=True)
class DecisionBlock:
    kind: BlockKind
    text: str


@dataclass(frozen=True)
class TextPiece:
    text: str


@dataclass(frozen=True)
class MarkerPiece:
    number: int


class DecisionBlocks:
    def split(self, full_text: str) -> list[DecisionBlock]:
        lines = full_text.split("\n")
        title_index = next((i for i, line in enumerate(lines) if _SPACED_TITLE.match(line)), -1)
        blocks: list[DecisionBlock] = []
        for index, line in enumerate(lines):
            if line.strip() == "":
                continue
            if title_index >= 0 and index < title_index:
                # Everything before the spaced title is the caption; the long line right before it is the parties.
                kind = BlockKind.PARTIES if index == title_index - 1 else BlockKind.CAPTION
                blocks.append(DecisionBlock(kind, line))
            elif index == title_index:
                blocks.append(DecisionBlock(BlockKind.TITLE, line.replace(" ", "")))
            elif title_index >= 0 and index == title_index + 1 and _PONENTE.search(line):
                blocks.append(DecisionBlock(BlockKind.PONENTE, line))
            elif _NOTICE.match(line):
                blocks.append(DecisionBlock(BlockKind.NOTICE, line.replace(" ", "")))
            elif _SIGNATURE.search(line) or _WE_CONCUR.match(line):
                blocks.append(DecisionBlock(BlockKind.SIGNATURE, line))
            elif self._is_heading(line, lines[index + 1] if index + 1 < len(lines) else None):
                blocks.append(DecisionBlock(BlockKind.HEADING, line))
            else:
                blocks.append(DecisionBlock(BlockKind.PARAGRAPH, line))
        return blocks

    @staticmethod
    def pieces(text: str) -> list[TextPiece | MarkerPiece]:
        """"...the CHED.[^3] On 19 June" -> text and footnote markers, in order."""
        out: list[TextPiece | MarkerPiece] = []
        last = 0
        for match in _MARKER.finditer(text):
            if match.start() > last:
                out.append(TextPiece(text[last : match.start()]))
            out.append(MarkerPiece(int(match.group(1))))
            last = match.end()
        if last < len(text):
            out.append(TextPiece(text[last:]))
        return out

    @staticmethod
    def _is_heading(line: str, following: str | None) -> bool:
        if len(line) > 80 or _END_PUNCTUATION.search(line) or _NOT_A_HEADING.match(line):
            return False
        if not _STARTS_LIKE_HEADING.match(line):
            return False
        return following is not None and len(following) >= min(len(line), _MIN_FOLLOWING_LINE)  # a real sentence follows
