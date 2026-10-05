"""A question a student asks about a case (in the AI assistant panel), and its checked answer."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from caselens.domain.digest import AnswerSentence

MAX_QUESTION = 500


class QuestionState(str, Enum):
    PENDING = "pending"  # being answered
    READY = "ready"  # answered; `sentences` may be empty: the decision does not say enough to answer it
    FAILED = "failed"  # not answered (the service did not answer, or the daily limit was reached): `error` says why


@dataclass
class CaseQuestion:
    case_id: int  # the MAIN case
    question: str
    batch_id: int | None = None  # the upload ("review") it was asked in, if any
    state: QuestionState = QuestionState.PENDING
    sentences: tuple[AnswerSentence, ...] = ()  # only sentences that passed every check, each citing the decision's paragraphs
    error: str | None = None
    id: int | None = None
    created_at: datetime | None = None
