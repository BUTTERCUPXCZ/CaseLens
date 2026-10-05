from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from caselens.application.ports.questions import CaseQuestionRepository
from caselens.domain.case_question import CaseQuestion, QuestionState
from caselens.domain.digest import AnswerSentence
from caselens.infrastructure.db.orm_models import CaseQuestionModel


def _entity(row: CaseQuestionModel) -> CaseQuestion:
    sentences = tuple(AnswerSentence(s["text"], tuple(s.get("cites", []))) for s in (row.answer or {}).get("sentences", []))
    return CaseQuestion(
        case_id=row.case_id, question=row.question, batch_id=row.batch_id, state=QuestionState(row.state), sentences=sentences,
        error=row.error, id=row.id, created_at=row.created_at,
    )


class SqlCaseQuestionRepository(CaseQuestionRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, question: CaseQuestion) -> CaseQuestion:
        row = CaseQuestionModel(case_id=question.case_id, batch_id=question.batch_id, question=question.question, state=question.state.value, error=question.error)
        self._session.add(row)
        self._session.flush()
        self._session.refresh(row)
        return _entity(row)

    def get(self, question_id: int) -> CaseQuestion | None:
        row = self._session.get(CaseQuestionModel, question_id)
        return _entity(row) if row else None

    def save(self, question: CaseQuestion) -> None:
        row = self._session.get(CaseQuestionModel, question.id)
        row.state, row.error = question.state.value, question.error
        row.answer = {"sentences": [{"text": s.text, "cites": list(s.cites)} for s in question.sentences]}
        self._session.flush()

    def list_for(self, case_id: int, batch_id: int | None) -> list[CaseQuestion]:
        same_batch = CaseQuestionModel.batch_id == batch_id if batch_id is not None else CaseQuestionModel.batch_id.is_(None)
        rows = self._session.scalars(select(CaseQuestionModel).where(CaseQuestionModel.case_id == case_id, same_batch).order_by(CaseQuestionModel.id))
        return [_entity(r) for r in rows]

    def count_since(self, since: datetime) -> int:
        return self._session.scalar(select(func.count()).select_from(CaseQuestionModel).where(CaseQuestionModel.created_at >= since)) or 0
