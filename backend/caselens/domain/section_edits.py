"""A student's own text for one section of a case digest, kept in their review.

Written as plain text: a blank line starts a new paragraph, a line starting "- " is a bullet point, a line starting "# " is a subheading
("# 1. The power is Congress's"). The same format is used to show the AI's text in the edit box, so editing starts from what is there."""
from caselens.domain.digest import AnswerSentence
from caselens.domain.digest_v2 import DigestBlock, DigestDraft, Section

MAX_SECTION_TEXT = 20_000


def section_text(blocks: tuple[DigestBlock, ...]) -> str:
    """The section as the student would type it."""
    parts: list[str] = []
    for block in blocks:
        lines: list[str] = []
        if block.heading:
            lines.append(f"# {block.heading}")
        if block.as_list:
            lines += [f"- {s.text}" for s in block.sentences]
        elif block.sentences:
            lines.append(" ".join(s.text for s in block.sentences))
        parts.append("\n".join(lines))
    return "\n\n".join(p for p in parts if p)


def parse_section_text(text: str) -> tuple[DigestBlock, ...]:
    """The student's text as blocks. Their sentences cite nothing: they are theirs, not checked against the decision."""
    blocks: list[DigestBlock] = []
    heading: str | None = None
    for chunk in (text or "").replace("\r\n", "\n").split("\n\n"):
        lines = [line.rstrip() for line in chunk.split("\n") if line.strip()]
        if not lines:
            continue
        if lines[0].lstrip().startswith("# "):
            heading = lines.pop(0).lstrip()[2:].strip() or None
            if not lines:
                continue  # a heading alone: it goes on the next paragraph
        bullets = [line.lstrip()[2:].strip() for line in lines if line.lstrip().startswith("- ")]
        if bullets and len(bullets) == len(lines):
            blocks.append(DigestBlock(tuple(AnswerSentence(b, ()) for b in bullets if b), heading, as_list=True))
        else:
            blocks.append(DigestBlock((AnswerSentence(" ".join(line.strip() for line in lines), ()),), heading))
        heading = None
    if heading:
        blocks.append(DigestBlock((), heading))
    return tuple(blocks)


def with_edits(draft: DigestDraft, edits: dict[Section, str]) -> DigestDraft:
    """The digest as this review shows it: the AI's sections, with the ones the student rewrote replaced (an empty text removes the section)."""
    sections = dict(draft.sections)
    for section, text in edits.items():
        blocks = parse_section_text(text)
        if blocks:
            sections[section] = blocks
        else:
            sections.pop(section, None)
    return DigestDraft({s: sections[s] for s in Section if s in sections})
