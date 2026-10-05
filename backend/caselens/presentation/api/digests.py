from fastapi import APIRouter, Depends, Response

from caselens.composition import Services
from caselens.domain.case_digest import CaseDigest, DigestStatus, DigestTemplate
from caselens.domain.services.digest_field_factory import DigestFieldFactory
from caselens.presentation.api.digest_schemas import (
    DigestOut,
    DigestRequestIn,
    PassageIn,
    QuestionIn,
    RegenerateIn,
    TextIn,
)
from caselens.presentation.dependencies import get_services

router = APIRouter(tags=["digests"])
_factory = DigestFieldFactory()


def _out(digest: CaseDigest, services: Services) -> DigestOut:
    case = services.get_case().execute(digest.case_id)
    return DigestOut.from_entity(digest, case, _factory.pickable_range(case.full_text))


@router.post("/cases/{case_id}/digest", response_model=DigestOut)
def request_digest(
    case_id: int, body: DigestRequestIn, response: Response, services: Services = Depends(get_services)
) -> DigestOut:
    """Start (or return) this case's digest. The Court's own text is in the response at once; the written
    explanations arrive in the background (status `pending`, each answer field `pending` until ready): poll
    `GET /digests/{id}`."""
    digest = services.request_case_digest().execute(
        case_id, body.upload_id, DigestTemplate(body.template), body.questions
    )
    if digest.status is DigestStatus.PENDING:
        response.status_code = 202
    return _out(digest, services)


@router.get("/cases/{case_id}/digest", response_model=DigestOut)
def get_case_digest(case_id: int, upload_id: int | None = None, services: Services = Depends(get_services)) -> DigestOut:
    return _out(services.get_digest().for_case(case_id, upload_id), services)


@router.get("/uploads/{upload_id}/digests", response_model=list[DigestOut])
def list_upload_digests(upload_id: int, services: Services = Depends(get_services)) -> list[DigestOut]:
    return [_out(d, services) for d in services.get_digest().for_upload(upload_id)]


@router.get("/digests/{digest_id}", response_model=DigestOut)
def get_digest(digest_id: int, services: Services = Depends(get_services)) -> DigestOut:
    return _out(services.get_digest().by_id(digest_id), services)


@router.put("/digests/{digest_id}/fields/{key}/text", response_model=DigestOut)
def write_field(digest_id: int, key: str, body: TextIn, services: Services = Depends(get_services)) -> DigestOut:
    """The student types over a field. It is marked as theirs; `reset` puts the system's version back."""
    return _out(services.edit_digest_field().write_text(digest_id, key, body.text), services)


@router.post("/digests/{digest_id}/fields/{key}/paste", response_model=DigestOut)
def paste_field(digest_id: int, key: str, body: TextIn, services: Services = Depends(get_services)) -> DigestOut:
    """The student pastes text into a Court-text field (Facts, Issue, Ruling, Doctrine). Marked as pasted."""
    return _out(services.edit_digest_field().paste_text(digest_id, key, body.text), services)


@router.put("/digests/{digest_id}/fields/{key}/passage", response_model=DigestOut)
def pick_passage(digest_id: int, key: str, body: PassageIn, services: Services = Depends(get_services)) -> DigestOut:
    """The student picks paragraphs of the decision. The text is read from the stored decision, never from the request."""
    return _out(services.edit_digest_field().pick_passage(digest_id, key, body.first, body.last), services)


@router.post("/digests/{digest_id}/fields/{key}/reset", response_model=DigestOut)
def reset_field(digest_id: int, key: str, services: Services = Depends(get_services)) -> DigestOut:
    return _out(services.edit_digest_field().reset(digest_id, key), services)


@router.post("/digests/{digest_id}/questions", response_model=DigestOut, status_code=202)
def ask_question(digest_id: int, body: QuestionIn, services: Services = Depends(get_services)) -> DigestOut:
    """Add a question of the student's own (any question in their reviewer). It is answered in the background."""
    return _out(services.edit_digest_field().ask(digest_id, body.question), services)


@router.post("/digests/{digest_id}/fields/{key}/suggest", response_model=DigestOut, status_code=202)
def suggest_passage(digest_id: int, key: str, services: Services = Depends(get_services)) -> DigestOut:
    """Look again for the Court's own passage of an empty Facts, Issue or Doctrine (the "Suggest for me" button)."""
    return _out(services.edit_digest_field().suggest(digest_id, key), services)


@router.post("/digests/{digest_id}/regenerate", response_model=DigestOut, status_code=202)
def regenerate(digest_id: int, body: RegenerateIn, services: Services = Depends(get_services)) -> DigestOut:
    return _out(services.edit_digest_field().regenerate(digest_id, body.keys), services)
