import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from caselens.composition import start_background_jobs
from caselens.domain import errors
from caselens.infrastructure.config import get_settings
from caselens.infrastructure.db.upload_cleanup import keep_uploads_trimmed
from caselens.presentation import access_gate
from caselens.presentation.api import bulk, case_digests, case_questions, catalog, cases, digests, health, insights, library, reviewer, uploads

# Domain error -> HTTP status. One table, so no router needs try/except.
_STATUS_BY_ERROR: list[tuple[type[errors.DomainError], int]] = [
    (errors.UnsupportedDocumentError, 415),
    (errors.DocumentExtractionError, 422),
    (errors.InvalidSourceUrlError, 400),
    (errors.CaseNotFoundError, 404),
    (errors.DigestNotFoundError, 404),
    (errors.InvalidDigestEditError, 422),
    (errors.AiUnavailableError, 503),
    (errors.JobQueueUnavailableError, 503),
    (errors.CaseParseError, 502),
    (errors.SourceUnavailableError, 502),
    (errors.DomainError, 400),
]


def _handle_domain_error(_: Request, exc: Exception) -> JSONResponse:
    status = next(code for error_type, code in _STATUS_BY_ERROR if isinstance(exc, error_type))
    return JSONResponse({"detail": str(exc)}, status_code=status)


@asynccontextmanager
async def _lifespan(_: FastAPI):
    if get_settings().queue_backend != "stub":  # tests never start background work
        start_background_jobs()
        if get_settings().upload_keep_days > 0:
            keep_uploads_trimmed(get_settings().upload_keep_days)
    yield


def create_app() -> FastAPI:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    app = FastAPI(title="CaseLens", version="0.1.0", lifespan=_lifespan)
    app.middleware("http")(access_gate.require_access_code)
    app.add_exception_handler(errors.DomainError, _handle_domain_error)
    for router in (health.router, access_gate.router, uploads.router, cases.router, library.router, catalog.router, insights.router, digests.router, reviewer.router, case_digests.router, case_questions.router, bulk.router):
        app.include_router(router)
    return app


app = create_app()
