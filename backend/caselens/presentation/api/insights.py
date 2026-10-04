from fastapi import APIRouter, Depends, Query

from caselens.composition import Services
from caselens.presentation.api.schemas import InsightsOut, TrendsOut
from caselens.presentation.dependencies import get_services

router = APIRouter(tags=["insights"])


@router.get("/cases/{case_id}/insights", response_model=InsightsOut)
def case_insights(case_id: int, services: Services = Depends(get_services)) -> InsightsOut:
    """Key findings for one stored case, parsed from its official text."""
    return InsightsOut.from_insights(services.get_case_insights().execute(case_id))


@router.get("/insights/trends", response_model=TrendsOut)
def trends(
    limit: int = Query(10, ge=1, le=100), services: Services = Depends(get_services)
) -> TrendsOut:
    """Patterns across every stored decision. `enough_data` is false until there are
    enough cases for the counts to mean anything."""
    return TrendsOut.from_report(services.get_trends().execute(limit))
