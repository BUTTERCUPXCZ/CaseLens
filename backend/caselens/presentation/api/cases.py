from fastapi import APIRouter, Depends, HTTPException, Response

from caselens.application.use_cases.search_case import SearchStatus
from caselens.composition import Services
from caselens.domain.value_objects import GrNumber
from caselens.presentation.api.schemas import (
    CaseDetailOut,
    CaseSummaryOut,
    FetchByUrlIn,
    SearchOut,
)
from caselens.presentation.dependencies import get_services

router = APIRouter(prefix="/cases", tags=["cases"])


@router.get("", response_model=SearchOut)
def search_cases(
    gr_no: str, response: Response, year: int | None = None, services: Services = Depends(get_services)
) -> SearchOut:
    """Search by G.R. number. A case we do not have yet is fetched in the background:
    202 + status "pending" means ask again shortly."""
    try:
        number = GrNumber(gr_no)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

    result = services.search_case().execute(number, year)
    if result.status is SearchStatus.PENDING:
        response.status_code = 202
    return SearchOut(
        status=result.status.value, cases=[CaseSummaryOut.from_entity(c) for c in result.cases]
    )


@router.post("/fetch", response_model=CaseDetailOut)
def fetch_case_by_url(body: FetchByUrlIn, services: Services = Depends(get_services)) -> CaseDetailOut:
    """Manual fallback: fetch and store one official Lawphil page by its URL."""
    return CaseDetailOut.from_entity(services.ingest_case().execute(body.url))


@router.get("/{case_id}", response_model=CaseDetailOut)
def get_case(case_id: int, services: Services = Depends(get_services)) -> CaseDetailOut:
    return CaseDetailOut.from_entity(services.get_case().execute(case_id))
