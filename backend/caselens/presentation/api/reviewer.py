import re

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel

from caselens.composition import Services
from caselens.domain.finished_reviewer import FinishedReviewer, ReviewerBox
from caselens.presentation.dependencies import get_services

router = APIRouter(prefix="/uploads", tags=["finished reviewer"])

_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class BoxRefOut(BaseModel):
    digest_id: int
    case_id: int
    citation_id: int
    title: str
    heading: str
    ready: bool

    @classmethod
    def from_box(cls, box: ReviewerBox) -> "BoxRefOut":
        return cls(
            digest_id=box.digest_id, case_id=box.case_id, citation_id=box.citation_id,
            title=box.title, heading=box.heading, ready=box.ready,
        )


class BlockOut(BaseModel):
    index: int
    text: str
    heading_level: int | None  # 1 = title, 2 and 3 = headings, None = body text
    boxes: list[BoxRefOut]  # the digests that go right after this paragraph


class FinishedReviewerOut(BaseModel):
    upload_id: int
    filename: str
    source: str  # "docx": the Word file gets the boxes inserted; "pdf"/"text": it is rebuilt as a new Word file
    blocks: list[BlockOut]
    unplaced: list[BoxRefOut]
    all_ready: bool
    own_digests: int  # digests the student already wrote inside the file (0 for a plain reviewer)

    @classmethod
    def from_entity(cls, reviewer: FinishedReviewer) -> "FinishedReviewerOut":
        boxes = reviewer.all_boxes()
        return cls(
            upload_id=reviewer.upload_id,
            filename=reviewer.filename,
            source=reviewer.source,
            blocks=[
                BlockOut(index=i, text=text, heading_level=reviewer.heading_levels[i] if i < len(reviewer.heading_levels) else None, boxes=[BoxRefOut.from_box(b) for b in reviewer.after_block.get(i, [])])
                for i, text in enumerate(reviewer.blocks)
            ],
            unplaced=[BoxRefOut.from_box(b) for b in reviewer.unplaced],
            all_ready=all(b.ready for b in boxes),
            own_digests=reviewer.own_digests,
        )


@router.get("/{upload_id}/document", response_model=FinishedReviewerOut)
def finished_reviewer(upload_id: int, services: Services = Depends(get_services)) -> FinishedReviewerOut:
    """The reviewer's paragraphs with the digest boxes placed after the paragraph that cites each case.
    Fetch each box's content with `GET /digests/{id}`."""
    return FinishedReviewerOut.from_entity(services.build_finished_reviewer().execute(upload_id))


@router.get("/{upload_id}/document.docx")
def download_finished_reviewer(upload_id: int, services: Services = Depends(get_services)) -> Response:
    """The finished reviewer as a Word file. Anything still being written is marked, so download again a moment later."""
    reviewer = services.build_finished_reviewer().execute(upload_id)
    data = services.reviewer_exporter().export(reviewer, services.original_upload(upload_id))
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", reviewer.filename.rsplit(".", 1)[0]).strip("-") or "reviewer"
    return Response(
        content=data,
        media_type=_DOCX,
        headers={"Content-Disposition": f'attachment; filename="{stem}-with-digests.docx"'},
    )
