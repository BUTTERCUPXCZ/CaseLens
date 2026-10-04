from fastapi import APIRouter, Depends, Query

from caselens.composition import Services
from caselens.presentation.api.schemas import CasePageOut
from caselens.presentation.dependencies import get_services

router = APIRouter(prefix="/library", tags=["library"])


@router.get("/cases", response_model=CasePageOut)
def library_cases(
    q: str | None = Query(None, max_length=200, description="Part of the case name, or the start of a G.R. number"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    services: Services = Depends(get_services),
) -> CasePageOut:
    """Every stored case, newest decision first. Lighter than GET /cases/{id}: no full text."""
    return CasePageOut.from_page(services.list_cases().execute(q, limit, offset))
