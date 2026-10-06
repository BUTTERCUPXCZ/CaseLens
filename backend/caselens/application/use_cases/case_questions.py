import logging
from collections.abc import Callable
from datetime import UTC, datetime

from caselens.application.ports.ai import AnswerRequest
from caselens.application.ports.gateways import JobQueue
from caselens.application.ports.questions import CaseQuestionRepository
from caselens.application.ports.repositories import CaseRepository, UnitOfWork
from caselens.application.use_cases.answer_case_question import AnswerCaseQuestion, decision_sources
from caselens.domain.case_question import MAX_QUESTION, CaseQuestion, QuestionState
from caselens.domain.errors import AiCreditError, AiUnavailableError, CaseNotFoundError, DomainError
from caselens.domain.services.heading_sections import HeadingSections

logger = logging.getLogger(__name__)


def _reason(exc: AiUnavailableError) -> str:
    """What the student reads: a credit problem says so (asking again cannot help); anything else is a passing outage."""
    return AiCreditError.STUDENT_MESSAGE if isinstance(exc, AiCreditError) else _SERVICE_DOWN

_MAX_SENTENCES = 4
_NO_ANSWERER = "Written answers are not set up on this server."
_SERVICE_DOWN = "The writing service did not answer. Ask again in a moment."
DAILY_LIMIT_MESSAGE = "The limit for questions today has been reached. Ask again tomorrow."


class AskAboutCase:
    """A student asks a question about a case (in a review, or on its own). The answer is written in the background from the decision."""

    def __init__(
        self,
        cases: CaseRepository,
        questions: CaseQuestionRepository,
        jobs: JobQueue,
        uow: UnitOfWork,
        daily_limit: int = 0,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._cases = cases
        self._questions = questions
        self._jobs = jobs
        self._uow = uow
        self._daily_limit = daily_limit
        self._clock = clock

    def execute(self, case_id: int, question: str, batch_id: int | None = None) -> CaseQuestion:
        text = " ".join(question.split())
        if len(text) < 3:
            raise DomainError("Write a question first.")
        if len(text) > MAX_QUESTION:
            raise DomainError(f"Keep the question under {MAX_QUESTION} characters.")
        found = self._cases.summaries([case_id]).get(case_id)
        if found is None:
            raise CaseNotFoundError(f"Case {case_id} does not exist.")
        asked = CaseQuestion(case_id=found.main_case_id or case_id, question=text, batch_id=batch_id)
        midnight = self._clock().astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        if self._daily_limit and self._questions.count_since(midnight) >= self._daily_limit:
            asked.state, asked.error = QuestionState.FAILED, DAILY_LIMIT_MESSAGE
        saved = self._questions.add(asked)
        self._uow.commit()  # commit first so the worker can see it
        if saved.state is QuestionState.PENDING:
            assert saved.id is not None
            self._jobs.enqueue_case_question(saved.id)
        return saved


class AnswerQueuedQuestion:
    """The background job: answer one question from the decision's own paragraphs. Every sentence must cite them and pass the checks
    (`AnswerCaseQuestion`); what fails is dropped. No sentence left means "the decision does not say enough", never a guess."""

    def __init__(self, cases: CaseRepository, questions: CaseQuestionRepository, answerer: AnswerCaseQuestion | None, uow: UnitOfWork) -> None:
        self._cases = cases
        self._questions = questions
        self._answerer = answerer
        self._uow = uow

    def execute(self, question_id: int) -> CaseQuestion | None:
        asked = self._questions.get(question_id)
        if asked is None or asked.state is not QuestionState.PENDING:
            return asked  # already settled (a message delivered twice)
        case = self._cases.get(asked.case_id)
        if case is None:
            return self._finish(asked, QuestionState.FAILED, f"Case {asked.case_id} no longer exists.")
        if self._answerer is None:
            return self._finish(asked, QuestionState.FAILED, _NO_ANSWERER)
        paragraphs = case.full_text.split("\n")
        start = HeadingSections.body_start(paragraphs) or 0
        sources = [s for s in decision_sources(paragraphs, start, len(paragraphs) - 1) if s.text.strip()]
        self._uow.commit()  # end the read before the AI call (minutes): SQLite refuses a late save from a read held that long
        try:
            answer = self._answerer.answer(AnswerRequest(asked.question, tuple(sources), _MAX_SENTENCES))
        except AiUnavailableError as exc:
            logger.warning("question %s: not answered: %s", question_id, exc)
            return self._finish(asked, QuestionState.FAILED, _reason(exc))
        for line in answer.dropped:
            logger.info("question %s: dropped a sentence (%s)", question_id, line.reason[:100])
        asked.sentences = answer.sentences
        return self._finish(asked, QuestionState.READY, None)

    def _finish(self, asked: CaseQuestion, state: QuestionState, error: str | None) -> CaseQuestion:
        asked.state, asked.error = state, error
        self._questions.save(asked)
        self._uow.commit()
        return asked


class ListCaseQuestions:
    def __init__(self, cases: CaseRepository, questions: CaseQuestionRepository) -> None:
        self._cases = cases
        self._questions = questions

    def execute(self, case_id: int, batch_id: int | None) -> list[CaseQuestion]:
        found = self._cases.summaries([case_id]).get(case_id)
        if found is None:
            raise CaseNotFoundError(f"Case {case_id} does not exist.")
        return self._questions.list_for(found.main_case_id or case_id, batch_id)
