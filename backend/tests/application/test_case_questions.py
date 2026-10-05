"""Asking about a case in the AI assistant panel: queued once, answered from the decision, every sentence checked (the AI is scripted)."""
from datetime import datetime

import pytest

from caselens.application.use_cases.answer_case_question import AnswerCaseQuestion
from caselens.application.use_cases.case_questions import DAILY_LIMIT_MESSAGE, AnswerQueuedQuestion, AskAboutCase, ListCaseQuestions
from caselens.domain.case_question import QuestionState
from caselens.domain.digest import AnswerSentence
from caselens.domain.errors import AiUnavailableError, CaseNotFoundError, DomainError
from tests.fakes import FakeJobQueue, FakeUnitOfWork, InMemoryCaseQuestionRepository, InMemoryCaseRepository, ScriptedWriter, VerdictChecker
from tests.helpers import parse_digest_case

GRANT = "WHEREFORE, we GRANT the petition"


class World:
    def __init__(self, sentences=(), writer_error=None, daily_limit=0, with_ai=True):
        self.cases, self.questions, self.jobs, self.uow = InMemoryCaseRepository(), InMemoryCaseQuestionRepository(), FakeJobQueue(), FakeUnitOfWork()
        self.case = self.cases.add(parse_digest_case("gr_180046_2009.html"))
        related = parse_digest_case("gr_180046_2009.html")
        related.source_url, related.main_case_id = "https://lawphil.net/other", self.case.id
        self.related = self.cases.add(related)
        self.writer, self.checker = ScriptedWriter(list(sentences), writer_error), VerdictChecker()
        answerer = AnswerCaseQuestion(self.writer, self.checker) if with_ai else None
        self.ask = AskAboutCase(self.cases, self.questions, self.jobs, self.uow, daily_limit, clock=lambda: datetime(2026, 10, 5, 12))
        self.answer = AnswerQueuedQuestion(self.cases, self.questions, answerer, self.uow)
        self.list = ListCaseQuestions(self.cases, self.questions)

    def paragraph(self, text: str) -> str:
        index = next(i for i, line in enumerate(self.case.full_text.split("\n")) if text in line)
        return f"P{index}"


def test_a_question_is_queued_once_on_the_main_case_and_answered_with_cited_checked_sentences():
    w = World()
    cite = w.paragraph(GRANT)
    w.writer.sentences = [AnswerSentence("The Court granted the petition.", (cite,))]
    asked = w.ask.execute(w.related.id, "  What did the Court   decide? ", batch_id=7)
    assert asked.case_id == w.case.id and asked.question == "What did the Court decide?" and asked.state is QuestionState.PENDING
    assert w.jobs.case_questions == [asked.id]

    answered = w.answer.execute(asked.id)
    assert answered.state is QuestionState.READY and [s.text for s in answered.sentences] == ["The Court granted the petition."]
    assert all(s.id.startswith("P") for s in w.writer.requests[0].sources)  # only the decision's own paragraphs
    assert [q.id for q in w.list.execute(w.case.id, 7)] == [asked.id] and w.list.execute(w.case.id, None) == []


def test_a_sentence_the_checker_rejects_is_dropped_and_nothing_left_means_no_answer_not_a_guess():
    w = World()
    cite = w.paragraph(GRANT)
    w.writer.sentences = [AnswerSentence("The Court awarded damages.", (cite,))]
    w.checker.unsupported = {"The Court awarded damages."}
    answered = w.answer.execute(w.ask.execute(w.case.id, "Were damages awarded?").id)
    assert answered.state is QuestionState.READY and answered.sentences == ()


def test_a_service_that_is_down_says_so_and_a_repeated_message_is_harmless():
    w = World(writer_error=AiUnavailableError("down"))
    asked = w.ask.execute(w.case.id, "What is the doctrine?")
    failed = w.answer.execute(asked.id)
    assert failed.state is QuestionState.FAILED and "did not answer" in failed.error
    assert w.answer.execute(asked.id).state is QuestionState.FAILED and len(w.writer.requests) == 1  # settled: not asked again


def test_without_an_ai_the_question_fails_with_a_plain_reason():
    w = World(with_ai=False)
    assert "not set up" in w.answer.execute(w.ask.execute(w.case.id, "Why?").id).error


def test_over_the_daily_limit_the_question_is_kept_with_the_reason_and_never_queued():
    w = World(daily_limit=1)
    w.ask.execute(w.case.id, "First question?")
    second = w.ask.execute(w.case.id, "Second question?")
    assert second.state is QuestionState.FAILED and second.error == DAILY_LIMIT_MESSAGE and w.jobs.case_questions == [1]


def test_an_empty_or_too_long_question_and_an_unknown_case_are_refused():
    w = World()
    with pytest.raises(DomainError):
        w.ask.execute(w.case.id, "  ")
    with pytest.raises(DomainError):
        w.ask.execute(w.case.id, "x" * 501)
    with pytest.raises(CaseNotFoundError):
        w.ask.execute(999, "Why?")
