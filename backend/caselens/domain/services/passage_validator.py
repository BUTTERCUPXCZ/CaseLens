"""The code checks on a paragraph range an AI pointed at. None of them needs an AI; they run before the second model
is asked, so an impossible pick costs nothing."""
from caselens.domain.digest import ParagraphRange

# The Court's own Facts run long (5 to 54 paragraphs on the hand-marked decisions) and a list of assigned errors can too; the box
# shows the first four and says so, and the student picks more. A range longer than this is not one passage.
MAX_PARAGRAPHS = {"facts": 60, "issues": 16, "doctrine": 3}
_MIN_CHARS = 20  # a range of only headings or markers is not a statement of anything
_MAX_CHARS = 8000  # a pasted-in statute or table run, not a passage


class PassageValidator:
    def check(self, key: str, picked: ParagraphRange, allowed: ParagraphRange, candidates: set[int], paragraphs: list[str]) -> str | None:
        """Why the pick cannot be used, or None if it passes."""
        if picked.first < allowed.first or picked.last > allowed.last:
            return f"paragraphs {picked.first}-{picked.last} are outside the body of the decision ({allowed.first}-{allowed.last})"
        if len(picked) > MAX_PARAGRAPHS[key]:
            return f"{len(picked)} paragraphs is more than a {key} passage should be ({MAX_PARAGRAPHS[key]})"
        if not set(picked.indexes()) <= candidates:
            return "a picked paragraph was not one of the paragraphs offered"
        texts = [paragraphs[i].strip() for i in picked.indexes()]
        if not any(len(text) >= _MIN_CHARS for text in texts):
            return "the picked paragraphs are only headings or markers"
        if sum(len(text) for text in texts) > _MAX_CHARS:
            return "the picked paragraphs are too long to be one passage"
        return None
