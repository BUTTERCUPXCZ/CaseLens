import logging
from datetime import date

from fastapi import APIRouter, Depends, Query

from caselens.composition import Services
from caselens.presentation.api.schemas import CatalogBuildOut, CatalogSearchOut, CatalogStatusOut
from caselens.presentation.dependencies import get_services

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/search", response_model=CatalogSearchOut)
def search_catalog(
    q: str = Query(..., max_length=200, description="Words from a case name, or a G.R. number"),
    year: int | None = Query(None, ge=1901, le=date.today().year),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    services: Services = Depends(get_services),
) -> CatalogSearchOut:
    """Search every decision on Lawphil's lists, 1987 to now, by case name or G.R. number.

    Answers from our own copy of the lists, so it is instant. Using it also keeps that copy
    fresh: the first search starts the one-time build; later searches ask for a refresh of
    the newest months at most once a day."""
    try:
        services.keep_catalog_fresh().execute()
    except Exception:  # noqa: BLE001  best effort: searching must work even if the queue is down
        logger.warning("could not ask for a catalog build/refresh", exc_info=True)
    page = services.search_catalog().execute(q, year, limit, offset)
    return CatalogSearchOut.from_page(page, services.catalog_status().execute())


@router.get("/status", response_model=CatalogStatusOut)
def catalog_status(services: Services = Depends(get_services)) -> CatalogStatusOut:
    return CatalogStatusOut.from_entity(services.catalog_status().execute())


@router.post("/build", response_model=CatalogBuildOut)
def build_catalog(services: Services = Depends(get_services)) -> CatalogBuildOut:
    """Start (or resume) reading Lawphil's monthly lists. Takes about 9 minutes the first time;
    a second request while one runs does nothing."""
    started = services.start_catalog_build().execute()
    return CatalogBuildOut(started=started, catalog=CatalogStatusOut.from_entity(services.catalog_status().execute()))
