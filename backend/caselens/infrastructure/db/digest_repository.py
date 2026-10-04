from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from caselens.application.ports.digests import DigestRepository
from caselens.domain.case_digest import (
    CaseDigest,
    DigestField,
    DigestStatus,
    DigestTemplate,
    FieldKind,
    FieldOrigin,
    FieldState,
    Passage,
)
from caselens.infrastructure.db.orm_models import DigestModel


def field_to_json(item: DigestField) -> dict:
    return {
        "key": item.key,
        "label": item.label,
        "kind": item.kind.value,
        "text": item.text,
        "origin": item.origin.value,
        "state": item.state.value,
        "cites": list(item.cites),
        "passage": None if item.passage is None else [item.passage.first, item.passage.last],
        "question": item.question,
        "note": item.note,
        "edited": item.edited,
        "original": None if item.original is None else field_to_json(item.original),
    }


def field_from_json(data: dict) -> DigestField:
    passage = data.get("passage")
    original = data.get("original")
    return DigestField(
        key=data["key"],
        label=data["label"],
        kind=FieldKind(data["kind"]),
        text=data.get("text", ""),
        origin=FieldOrigin(data.get("origin", "empty")),
        state=FieldState(data.get("state", "ready")),
        cites=tuple(data.get("cites", [])),
        passage=None if passage is None else Passage(passage[0], passage[1]),
        question=data.get("question"),
        note=data.get("note"),
        edited=data.get("edited", False),
        original=None if original is None else field_from_json(original),
    )


def _to_entity(row: DigestModel) -> CaseDigest:
    return CaseDigest(
        id=row.id,
        case_id=row.case_id,
        upload_id=row.upload_id,
        template=DigestTemplate(row.template),
        status=DigestStatus(row.status),
        fields=[field_from_json(f) for f in row.fields],
        error=row.error,
        model=row.model,
        prompt_version=row.prompt_version,
        parser_version=row.parser_version,
        ai_answered_at=row.ai_answered_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _fill(row: DigestModel, digest: CaseDigest) -> None:
    row.case_id = digest.case_id
    row.upload_id = digest.upload_id
    row.template = digest.template.value
    row.status = digest.status.value
    row.error = digest.error
    row.fields = [field_to_json(f) for f in digest.fields]
    row.model = digest.model
    row.prompt_version = digest.prompt_version
    row.parser_version = digest.parser_version
    row.ai_answered_at = digest.ai_answered_at
    row.updated_at = func.now()


class SqlDigestRepository(DigestRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, digest_id: int) -> CaseDigest | None:
        row = self._session.get(DigestModel, digest_id)
        return None if row is None else _to_entity(row)

    def find(self, case_id: int, upload_id: int | None) -> CaseDigest | None:
        query = select(DigestModel).where(DigestModel.case_id == case_id)
        query = query.where(DigestModel.upload_id.is_(None) if upload_id is None else DigestModel.upload_id == upload_id)
        row = self._session.scalars(query).first()
        return None if row is None else _to_entity(row)

    def add(self, digest: CaseDigest) -> CaseDigest:
        row = DigestModel()
        _fill(row, digest)
        self._session.add(row)
        self._session.flush()
        self._session.refresh(row)
        return _to_entity(row)

    def save(self, digest: CaseDigest) -> None:
        row = self._session.get(DigestModel, digest.id)
        if row is None:
            raise LookupError(f"Digest {digest.id} is not stored.")
        _fill(row, digest)
        self._session.flush()

    def list_for_upload(self, upload_id: int) -> list[CaseDigest]:
        rows = self._session.scalars(
            select(DigestModel).where(DigestModel.upload_id == upload_id).order_by(DigestModel.id)
        )
        return [_to_entity(r) for r in rows]

    def count_ai_since(self, since: datetime) -> int:
        return self._session.scalar(select(func.count()).where(DigestModel.ai_answered_at >= since)) or 0
