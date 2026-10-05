from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from caselens.composition import Services
from caselens.domain.case_question import MAX_QUESTION, CaseQuestion
from caselens.presentation.dependencies import get_services

router = APIRouter(tags=["questions"])


class AskIn(BaseModel):
    question: str = Field(..., min_length=1, max_length=MAX_QUESTION)
    batch_id: int | None = None  # the review (upload) it is asked in


class AnswerSentenceOut(BaseModel):
    text: str
    cites: list[str]  # P12 = paragraph 12 of the decision


class QuestionOut(BaseModel):
    id: int
    case_id: int
    batch_id: int | None
    question: str
    state: Literal["pending", "ready", "failed"]  # ready with no sentences: the decision does not say enough to answer it
    sentences: list[AnswerSentenceOut]
    error: str | None
    created_at: datetime | None

    @classmethod
    def from_entity(cls, q: CaseQuestion) -> "QuestionOut":
        return cls(
            id=q.id, case_id=q.case_id, batch_id=q.batch_id, question=q.question, state=q.state.value,
            sentences=[AnswerSentenceOut(text=s.text, cites=list(s.cites)) for s in q.sentences], error=q.error, created_at=q.created_at,
        )


@router.post("/cases/{case_id}/questions", response_model=QuestionOut, status_code=202)
def ask_about_case(case_id: int, body: AskIn, services: Services = Depends(get_services)) -> QuestionOut:
    """Ask a question about a case. It is answered in the background from the decision (a few seconds); poll GET for the answer."""
    return QuestionOut.from_entity(services.ask_about_case().execute(case_id, body.question, body.batch_id))


@router.get("/cases/{case_id}/questions", response_model=list[QuestionOut])
def case_questions(
    case_id: int, batch_id: int | None = Query(None, description="The review the questions were asked in"), services: Services = Depends(get_services)
) -> list[QuestionOut]:
    """The questions asked about a case in one review, oldest first, with their answers."""
    return [QuestionOut.from_entity(q) for q in services.list_case_questions().execute(case_id, batch_id)]
