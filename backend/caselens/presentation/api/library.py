from fastapi import APIRouter, Depends, Query

from caselens.composition import Services
from caselens.presentation.api.schemas import CasePageOut, SubjectCountOut, SubjectOut
from caselens.presentation.dependencies import get_services

router = APIRouter(prefix="/library", tags=["library"])


@router.get("/cases", response_model=CasePageOut)
def library_cases(
    q: str | None = Query(None, max_length=200, description="Part of the case name, or the start of a G.R. number"),
    subject_id: int | None = Query(None, description="Only the cases filed under this subject"),
    no_subject: bool = Query(False, description="Only the cases with no subject yet"),
    batch_id: int | None = Query(None, description="Only what this bulk upload gave: its main cases, each once"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    services: Services = Depends(get_services),
) -> CasePageOut:
    """One row per main case, newest decision first. Lighter than GET /cases/{id}: no full text. A Resolution or a repeat of the same
    case is never listed on its own."""
    if batch_id is not None:
        page = services.list_batch_cases().execute(batch_id, limit, offset)
    else:
        page = services.list_cases().execute(q, limit, offset, subject_id, no_subject)
    return CasePageOut.from_page(page, services.case_digest_states([c.id for c in page.items]))


@router.get("/subjects", response_model=list[SubjectCountOut])
def library_subjects(services: Services = Depends(get_services)) -> list[SubjectCountOut]:
    """The filter rail: every subject with the number of cases filed under it, and the cases with no subject yet."""
    return [SubjectCountOut(subject_id=c.subject_id, name=c.name, count=c.count) for c in services.list_subjects().execute()]


@router.get("/subject-list", response_model=list[SubjectOut])
def subject_list(services: Services = Depends(get_services)) -> list[SubjectOut]:
    """The subjects, for a picker."""
    return [SubjectOut(id=s.id, name=s.name) for s in services.get_subjects().execute()]
