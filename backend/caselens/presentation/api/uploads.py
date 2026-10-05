from fastapi import APIRouter, Depends, HTTPException, Query, Response, UploadFile

from caselens.composition import Services
from caselens.infrastructure.config import get_settings
from caselens.presentation.api.schemas import FetchByUrlIn, UploadOut, UploadSummaryOut
from caselens.presentation.dependencies import get_services

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("", response_model=UploadOut)
def create_upload(
    file: UploadFile, response: Response, services: Services = Depends(get_services)
) -> UploadOut:
    """Upload a PDF/DOCX. Known citations are checked now; the rest finish in the
    background (poll GET /uploads/{id}). 202 means "still processing"."""
    max_bytes = get_settings().upload_max_mb * 1024 * 1024
    data = file.file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(413, f"File is larger than {get_settings().upload_max_mb} MB.")

    upload = services.process_upload().execute(file.filename or "upload", data)
    if upload.status == "processing":
        response.status_code = 202
    return UploadOut.from_report(services.get_upload().execute(upload.id))


@router.get("", response_model=list[UploadSummaryOut])
def list_uploads(
    limit: int = Query(20, ge=1, le=100), services: Services = Depends(get_services)
) -> list[UploadSummaryOut]:
    """Recent uploads, newest first, each with how its citations came out."""
    return [UploadSummaryOut.from_entity(s) for s in services.list_uploads().execute(limit)]


@router.get("/{upload_id}", response_model=UploadOut)
def get_upload(upload_id: int, services: Services = Depends(get_services)) -> UploadOut:
    return UploadOut.from_report(services.get_upload().execute(upload_id))


@router.delete("/{upload_id}", status_code=204)
def delete_upload(upload_id: int, services: Services = Depends(get_services)) -> Response:
    """Remove a reviewer and its digest boxes. The cases it cited stay in the library."""
    services.delete_upload().execute(upload_id)
    return Response(status_code=204)


@router.post("/{upload_id}/retry", response_model=UploadOut)
def retry_upload(upload_id: int, services: Services = Depends(get_services)) -> UploadOut:
    """Check again the citations that could not be checked (source down, page unreadable)."""
    services.retry_upload().execute(upload_id)
    return UploadOut.from_report(services.get_upload().execute(upload_id))


@router.post("/{upload_id}/citations/{citation_id}/attach", response_model=UploadOut)
def attach_case(
    upload_id: int,
    citation_id: int,
    body: FetchByUrlIn,
    services: Services = Depends(get_services),
) -> UploadOut:
    """The student pastes the Lawphil link for a citation that could not be found."""
    services.attach_case_to_citation().execute(upload_id, citation_id, body.url)
    return UploadOut.from_report(services.get_upload().execute(upload_id))
