"""The student's reviewer with a digest box placed after each citing paragraph: the model both the on-screen
view and the Word file are built from."""
from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class BoxField:
    label: str
    text: str  # empty: the student fills it in (the Word file keeps the label, like "TOPIC EXPLAINED:" in their own boxes)
    note: str | None = None  # "Drafted from the decision (paragraphs 12, 14). Check it." / "Still being written."


@dataclass(frozen=True)
class ReviewerBox:
    digest_id: int
    case_id: int
    citation_id: int
    title: str  # "Digest 2: Facts, Issue, Ruling and Doctrine"
    heading: str  # the Court's record: "Review Center Associations ..., G.R. No. 180046 (April 2, 2009)"
    source_url: str
    decided_on: date | None
    check_note: str | None  # where the student's citation differs from the Court's record, in plain words
    fields: tuple[BoxField, ...]
    ready: bool  # False while the written answers are still being produced


@dataclass
class FinishedReviewer:
    upload_id: int
    filename: str
    source: str  # "docx" (boxes go into a copy of the student's file), "pdf" or "text" (rebuilt as a new Word file)
    blocks: list[str]  # the reviewer's paragraphs, in order (for "docx" these are the file's own paragraphs)
    after_block: dict[int, list[ReviewerBox]] = field(default_factory=dict)
    unplaced: list[ReviewerBox] = field(default_factory=list)  # boxes whose citation could not be found in a paragraph
    heading_levels: list[int | None] = field(default_factory=list)  # 1 title, 2, 3, or None for body text; same length as blocks
    own_digests: int = 0  # digests the student already wrote inside the uploaded file

    def all_boxes(self) -> list[ReviewerBox]:
        placed = [box for index in sorted(self.after_block) for box in self.after_block[index]]
        return placed + self.unplaced
