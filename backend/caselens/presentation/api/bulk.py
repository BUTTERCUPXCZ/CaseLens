from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, UploadFile
from pydantic import BaseModel, Field

from caselens.application.use_cases.bulk import MAX_FILES_PER_REQUEST, BulkView
from caselens.composition import Services
from caselens.domain.bulk import BulkItem, ItemStatus
from caselens.domain.digest_v2 import scope_key
from caselens.domain.services.case_names import short_case_name
from caselens.presentation.api.schemas import SubjectOut
from caselens.infrastructure.config import get_settings
from caselens.presentation.dependencies import get_services

router = APIRouter(prefix="/bulk", tags=["bulk"])


class BulkStartIn(BaseModel):
    text: str = ""  # pasted G.R. numbers, one per line or separated by commas
    subject_ids: list[int] = Field(default_factory=list, max_length=20)  # the tags for every case of this upload (may be none)
    topic_scope: str = Field("", max_length=300)  # narrows every digest of this upload to one doctrine or issue
    kind: Literal["individual", "bulk"] = "bulk"  # individual: one case, opened for its full text


class BulkCountsOut(BaseModel):
    total: int
    queued: int
    found: int
    duplicate: int
    not_found: int
    unreadable: int
    failed: int
    digests_ready: int
    digests_pending: int
    digests_failed: int


class BulkCaseNameOut(BaseModel):
    name: str  # "Review Center Association of the Philippines v. Ermita"
    gr_no: str


class BulkOut(BaseModel):
    id: int
    created_at: datetime | None
    subjects: list[SubjectOut]  # the tags chosen for this upload
    topic_scope: str  # "" = the standard digest
    kind: Literal["individual", "bulk"]
    labels: list[str]  # the first few files or numbers given
    cases: list[BulkCaseNameOut]  # the first few cases it gave, by name and G.R. number
    case_total: int  # how many cases it gave in all
    counts: BulkCountsOut
    finished: bool  # nothing is waiting for Lawphil any more (digests may still be written)

    @classmethod
    def from_view(cls, view: BulkView, services: Services) -> "BulkOut":
        c = view.counts
        return cls(
            id=view.batch.id, created_at=view.batch.created_at, finished=c.finished,
            subjects=[SubjectOut(id=s.id, name=s.name) for s in services.subjects_named(view.batch.subject_ids)],
            topic_scope=view.batch.topic_scope, kind=view.batch.kind, labels=list(view.labels),  # type: ignore[arg-type]
            cases=[BulkCaseNameOut(name=name, gr_no=gr_no) for name, gr_no in view.cases], case_total=view.case_total,
            counts=BulkCountsOut(
                total=c.total, queued=c.queued, found=c.found, duplicate=c.duplicate, not_found=c.not_found, unreadable=c.unreadable,
                failed=c.failed, digests_ready=c.digests_ready, digests_pending=c.digests_pending, digests_failed=c.digests_failed,
            ),
        )


class BulkCaseOut(BaseModel):
    id: int
    name: str
    gr_no: str
    subjects: list[SubjectOut]


class BulkItemOut(BaseModel):
    id: int
    position: int
    kind: Literal["gr_number", "file"]
    label: str
    gr_no: str | None
    status: Literal["queued", "found", "duplicate", "not_found", "unreadable", "failed"]
    message: str | None
    case: BulkCaseOut | None
    digest: Literal["none", "pending", "ready", "failed"] | None  # of the found case; None when there is no case


class BulkItemsOut(BaseModel):
    items: list[BulkItemOut]
    total: int


def _items_out(services: Services, items: list[BulkItem], scope: str) -> list[BulkItemOut]:
    case_ids = [i.case_id for i in items if i.case_id is not None]
    summaries = services.case_summaries(case_ids)
    states = services.case_digest_states(case_ids, scope_key(scope))
    out = []
    for item in items:
        case = summaries.get(item.case_id) if item.case_id is not None else None
        out.append(BulkItemOut(
            id=item.id, position=item.position, kind=item.kind.value, label=item.label, gr_no=item.gr_no, status=item.status.value, message=item.message,
            case=BulkCaseOut(id=case.id, name=short_case_name(case.title), gr_no=str(case.gr_no), subjects=[SubjectOut(id=s.id, name=s.name) for s in case.subjects]) if case else None,
            digest=(states.get(item.case_id, "none") if item.case_id is not None and item.status is ItemStatus.FOUND else None),  # type: ignore[arg-type]
        ))
    return out


@router.post("", response_model=BulkOut, status_code=201)
def start_bulk(body: BulkStartIn, services: Services = Depends(get_services)) -> BulkOut:
    """Start a bulk upload. Pasted G.R. numbers are queued at once; send decision files next with POST /bulk/{id}/files. Each number or
    file becomes ONE main case; the cases a decision only cites are never added."""
    batch = services.start_bulk_batch().execute(body.text, body.subject_ids, body.topic_scope, body.kind)
    return BulkOut.from_view(services.get_bulk_batch().execute(batch.id), services)


@router.post("/{batch_id}/files", response_model=BulkItemsOut, status_code=202)
def add_bulk_files(batch_id: int, files: list[UploadFile], services: Services = Depends(get_services)) -> BulkItemsOut:
    """Add decision files (PDF or Word), a few at a time (the web host limits one request to about 4 MB)."""
    if len(files) > MAX_FILES_PER_REQUEST:
        raise HTTPException(400, f"Send at most {MAX_FILES_PER_REQUEST} files at a time.")
    limit = get_settings().upload_max_mb * 1024 * 1024
    data: list[tuple[str, bytes]] = []
    for upload in files:
        content = upload.file.read(limit + 1)
        if len(content) > limit:
            raise HTTPException(413, f"{upload.filename} is larger than {get_settings().upload_max_mb} MB.")
        data.append((upload.filename or "file", content))
    items = services.add_bulk_files().execute(batch_id, data)
    return BulkItemsOut(items=_items_out(services, items, services.get_bulk_batch().execute(batch_id).batch.topic_scope), total=len(items))


@router.get("", response_model=list[BulkOut])
def recent_batches(limit: int = Query(10, ge=1, le=50), offset: int = Query(0, ge=0), services: Services = Depends(get_services)) -> list[BulkOut]:
    """The uploads, newest first ("My reviews")."""
    return [BulkOut.from_view(v, services) for v in services.get_bulk_batch().recent(limit, offset)]


@router.get("/{batch_id}", response_model=BulkOut)
def get_bulk(batch_id: int, services: Services = Depends(get_services)) -> BulkOut:
    """Progress of a bulk upload: how each item ended so far, and how the digests are coming along. Poll until `finished`."""
    return BulkOut.from_view(services.get_bulk_batch().execute(batch_id), services)


@router.get("/{batch_id}/items", response_model=BulkItemsOut)
def bulk_items(
    batch_id: int,
    status: ItemStatus | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    services: Services = Depends(get_services),
) -> BulkItemsOut:
    items, total = services.get_bulk_batch().items(batch_id, status, limit, offset)
    return BulkItemsOut(items=_items_out(services, items, services.get_bulk_batch().execute(batch_id).batch.topic_scope), total=total)


@router.post("/{batch_id}/retry")
def retry_bulk(batch_id: int, services: Services = Depends(get_services)) -> dict:
    """Queue again the items Lawphil could not answer for."""
    return {"requeued": services.retry_bulk_batch().execute(batch_id)}


@router.delete("/{batch_id}", status_code=204)
def delete_bulk(batch_id: int, services: Services = Depends(get_services)) -> Response:
    """Remove an upload from "My reviews", with the questions asked in it. Its cases and their digests stay in the library."""
    services.get_bulk_batch().delete(batch_id, services.unit_of_work())
    return Response(status_code=204)
