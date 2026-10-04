import re

_MAX_CHARS = 1200


class ReviewerPassageFinder:
    """The student's own words around a citation: the paragraph of the reviewer that cites the case, with the
    heading line before it when there is one. It tells the answer which topic the case is cited for.

    Pure text work on what the student uploaded; nothing here is looked up or guessed.
    """

    def find(self, upload_text: str, raw_citation: str) -> str | None:
        position = upload_text.find(raw_citation)
        if position < 0:
            # the extractor may have re-flowed whitespace: compare with whitespace squeezed
            squeezed_text = re.sub(r"\s+", " ", upload_text)
            squeezed_citation = re.sub(r"\s+", " ", raw_citation).strip()
            position = squeezed_text.find(squeezed_citation)
            if position < 0:
                return None
            upload_text = squeezed_text

        start = upload_text.rfind("\n\n", 0, position)
        start = 0 if start < 0 else start + 2
        end = upload_text.find("\n\n", position)
        end = len(upload_text) if end < 0 else end
        passage = upload_text[start:end].strip()

        heading_end = start - 2
        if heading_end > 0:  # the paragraph before, if it is a short line, is the section heading
            heading_start = upload_text.rfind("\n\n", 0, heading_end)
            heading = upload_text[0 if heading_start < 0 else heading_start + 2 : heading_end].strip()
            if heading and len(heading) <= 120 and "\n" not in heading:
                passage = f"{heading}\n{passage}"
        return passage[:_MAX_CHARS] or None
