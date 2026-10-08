from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from caselens.application.ports.digests import CaseDigestRepository
from caselens.domain.digest import AnswerSentence
from caselens.domain.digest_v2 import CaseDigestV2, DigestBlock, DigestDraft, DigestStage, DigestState, Section
from caselens.infrastructure.db.orm_models import CaseDigestV2Model


def draft_to_json(draft: DigestDraft) -> dict:
    return {
        section.value: [
            {"heading": block.heading, "list": block.as_list, "sentences": [{"text": s.text, "cites": list(s.cites), **({"key": True} if s.key else {})} for s in block.sentences]}
            for block in blocks
        ]
        for section, blocks in draft.sections.items()
    }


def draft_from_json(data: dict) -> DigestDraft:
    draft = DigestDraft()
    for section in Section:
        blocks = data.get(section.value) or []
        if blocks:
            draft.sections[section] = tuple(
                DigestBlock(
                    tuple(AnswerSentence(s["text"], tuple(s.get("cites", [])), bool(s.get("key"))) for s in block.get("sentences", [])),
                    block.get("heading"),
                    bool(block.get("list")),
                )
                for block in blocks
            )
    return draft


def _to_entity(row: CaseDigestV2Model) -> CaseDigestV2:
    return CaseDigestV2(
        id=row.id, case_id=row.case_id, scope=row.scope or "", state=DigestState(row.state), draft=draft_from_json(row.sections or {}),
        written=row.written, dropped=row.dropped, error=row.error, model=row.model, prompt_version=row.prompt_version,
        input_tokens=row.input_tokens, output_tokens=row.output_tokens, created_at=row.created_at, updated_at=row.updated_at,
        stage=DigestStage(row.stage) if row.stage else None, stage_at=row.stage_at,
    )


class SqlCaseDigestRepository(CaseDigestRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, case_id: int, scope_key: str = "") -> CaseDigestV2 | None:
        row = self._row(case_id, scope_key)
        return _to_entity(row) if row else None

    def get_by_id(self, digest_id: int) -> CaseDigestV2 | None:
        row = self._session.get(CaseDigestV2Model, digest_id)
        return _to_entity(row) if row else None

    def _row(self, case_id: int, key: str) -> CaseDigestV2Model | None:
        return self._session.scalar(select(CaseDigestV2Model).where(CaseDigestV2Model.case_id == case_id, CaseDigestV2Model.scope_key == key))

    def save(self, digest: CaseDigestV2) -> CaseDigestV2:
        row = self._row(digest.case_id, digest.scope_key)
        if row is None:
            row = CaseDigestV2Model(case_id=digest.case_id, scope=digest.scope, scope_key=digest.scope_key)
            self._session.add(row)
        row.state = digest.state.value
        row.sections = draft_to_json(digest.draft)
        row.written, row.dropped, row.error = digest.written, digest.dropped, digest.error
        row.model, row.prompt_version = digest.model, digest.prompt_version
        row.input_tokens, row.output_tokens = digest.input_tokens, digest.output_tokens
        row.stage, row.stage_at = (digest.stage.value if digest.stage else None), digest.stage_at
        row.updated_at = func.now()
        self._session.flush()
        self._session.refresh(row)
        return _to_entity(row)

    def set_stage(self, digest_id: int, stage: DigestStage, at: datetime) -> None:
        self._session.execute(update(CaseDigestV2Model).where(CaseDigestV2Model.id == digest_id).values(stage=stage.value, stage_at=at))

    def count_started_since(self, since: datetime) -> int:
        return self._session.scalar(select(func.count()).select_from(CaseDigestV2Model).where(CaseDigestV2Model.created_at >= since)) or 0

    def ready_case_ids(self, case_ids: Sequence[int], scope_key: str = "") -> set[int]:
        return {case_id for case_id, state in self.states(case_ids, scope_key).items() if state == DigestState.READY.value}

    def states(self, case_ids: Sequence[int], scope_key: str = "") -> dict[int, str]:
        if not case_ids:
            return {}
        rows = self._session.execute(
            select(CaseDigestV2Model.case_id, CaseDigestV2Model.state).where(
                CaseDigestV2Model.case_id.in_(list(case_ids)), CaseDigestV2Model.scope_key == scope_key
            )
        )
        return {case_id: state for case_id, state in rows}
