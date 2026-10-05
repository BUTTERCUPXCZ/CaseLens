import re

from caselens.application.ports.digests import DigestRepository
from caselens.application.ports.gateways import ReviewerBlockReader
from caselens.application.ports.repositories import CaseRepository, UploadRepository
from caselens.domain.case_digest import CaseDigest, DigestField, DigestStatus, DigestTemplate, FieldKind, FieldOrigin, FieldState
from caselens.domain.entities import CaseSummary, UploadedCitation
from caselens.domain.errors import CaseNotFoundError
from caselens.domain.finished_reviewer import BoxField, FinishedReviewer, ReviewerBox
from caselens.domain.services.reviewer_headings import ReviewerHeadings
from caselens.domain.services.reviewer_placement import CitationPlacer, CitationRef
from caselens.domain.value_objects import MatchStatus

_MARKER = re.compile(r"\[\^\d+\]")  # footnote markers like [^3]: left out of the Word file (the text is otherwise untouched)
_TEMPLATE_TITLE = {
    DigestTemplate.FACTS_AND_DOCTRINE: "Facts and Doctrine",
    DigestTemplate.FULL: "Facts, Issue, Ruling and Doctrine",
}
_CHECKED = (MatchStatus.MATCH, MatchStatus.MISMATCH)
_MAX_TITLE_NOTE_CHARS = 120


class BuildFinishedReviewer:
    """Puts each digest box after the paragraph of the student's reviewer that cites its case, and describes every
    box in plain terms (header from the Court's record, fields, where each answer came from).

    Used both for the on-screen "Finished reviewer" and for the Word file, so they always agree.
    """

    def __init__(
        self,
        uploads: UploadRepository,
        digests: DigestRepository,
        cases: CaseRepository,
        reader: ReviewerBlockReader,
        placer: CitationPlacer | None = None,
    ) -> None:
        self._uploads = uploads
        self._digests = digests
        self._cases = cases
        self._reader = reader
        self._placer = placer or CitationPlacer()

    def execute(self, upload_id: int) -> FinishedReviewer:
        upload = self._uploads.get(upload_id)
        if upload is None:
            raise CaseNotFoundError(f"Upload {upload_id} does not exist.")
        data = self._uploads.get_file_data(upload_id)
        if data is not None:
            blocks = self._reader.blocks(upload.filename, data)
            source = "docx" if upload.filename.lower().endswith(".docx") else "pdf"
        else:  # an upload from before the original file was kept: rebuild from the stored text
            blocks = [part.strip() for part in re.split(r"\n\s*\n", upload.text) if part.strip()]
            source = "text"

        refs = [
            CitationRef(c.id, c.claimed.raw, c.matched_case_id if c.status in _CHECKED else None)
            for c in upload.citations
        ]
        placement = self._placer.place(blocks, refs)
        by_citation = {c.id: c for c in upload.citations}
        digests = {d.case_id: d for d in self._digests.list_for_upload(upload_id)}
        summaries = self._cases.summaries(sorted({c.matched_case_id for c in upload.citations if c.matched_case_id}))

        headings = ReviewerHeadings()
        reviewer = FinishedReviewer(upload_id, upload.filename, source, blocks)
        reviewer.heading_levels = [headings.level(b, i) for i, b in enumerate(blocks)]
        reviewer.own_digests = headings.own_digest_count(blocks)
        number = 0

        def box_for(citation_id: int) -> ReviewerBox | None:
            nonlocal number
            citation = by_citation[citation_id]
            digest = digests.get(citation.matched_case_id)
            summary = summaries.get(citation.matched_case_id)
            if digest is None or summary is None:
                return None  # no digest was requested for this case: nothing to show
            number += 1
            return self._box(number, citation, digest, summary)

        for index in sorted(placement.after_block):
            boxes = [b for b in (box_for(cid) for cid in placement.after_block[index]) if b]
            if boxes:
                reviewer.after_block[index] = boxes
        reviewer.unplaced = [b for b in (box_for(cid) for cid in placement.unplaced) if b]
        return reviewer

    @staticmethod
    def _box(number: int, citation: UploadedCitation, digest: CaseDigest, summary: CaseSummary) -> ReviewerBox:
        title = (summary.title or "").rstrip(" .")  # the Court's caption ends with "Respondents."
        official = ", ".join(part for part in (title, f"G.R. No. {summary.gr_no.value}") if part)
        if summary.decision_date:
            official += f" ({summary.decision_date.strftime('%B %-d, %Y')})"
        return ReviewerBox(
            digest_id=digest.id,
            case_id=digest.case_id,
            citation_id=citation.id,
            title=f"Digest {number}: {_TEMPLATE_TITLE[digest.template]}",
            heading=official,
            source_url=summary.source_url,
            decided_on=summary.decision_date,
            check_note=_check_note(citation),
            fields=tuple(_box_field(f) for f in digest.fields),
            ready=digest.status is DigestStatus.READY and all(f.state is not FieldState.PENDING for f in digest.fields),
        )


def _check_note(citation: UploadedCitation) -> str | None:
    if not citation.mismatches:
        return None
    parts = [
        f"{key.replace('_', ' ')}: your reviewer says {values.get('claimed')}; the Court's record says {values.get('official')}"
        for key, values in citation.mismatches.items()
        # a "title" the reader took from the sentence before the citation is often a whole sentence, not a case name
        if key != "title" or len(str(values.get("claimed") or "")) <= _MAX_TITLE_NOTE_CHARS
    ]
    return ("Check this citation. " + "; ".join(parts) + ".") if parts else None


def _box_field(item: DigestField) -> BoxField:
    text = _MARKER.sub("", item.text)
    if item.state is FieldState.PENDING:
        return BoxField(item.label, "", "Still looking for the Court's passage." if item.kind is FieldKind.VERBATIM else "Still being written.")
    if item.state is FieldState.UNAVAILABLE:
        return BoxField(item.label, "", item.note)
    if item.origin is FieldOrigin.AI_DRAFTED:
        return BoxField(item.label, text, f"Drafted from the decision{_sources(item)}. Check it.")
    if item.origin is FieldOrigin.COURT_SUGGESTED:
        return BoxField(item.label, text, "The Court's own words, suggested from the decision: check it.")
    if item.origin is FieldOrigin.STUDENT_PASTED:
        return BoxField(item.label, text, "Pasted by you.")
    return BoxField(item.label, text, None)  # the Court's own text, or the student's own writing: no label needed


def _sources(item: DigestField) -> str:
    paragraphs = [c[1:] for c in item.cites if c.startswith("P")]
    shown = ", ".join(paragraphs[:6]) + (" and more" if len(paragraphs) > 6 else "")
    if not paragraphs:
        return ""
    return f" (decision paragraph {shown})" if len(paragraphs) == 1 else f" (decision paragraphs {shown})"
