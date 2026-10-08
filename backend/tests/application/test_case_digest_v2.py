"""Asking for, writing and reading the case digest of a main case (the AI is scripted)."""
from datetime import datetime

import pytest

from caselens.application.use_cases.case_digest_v2 import BuildCaseDigestV2, GetCaseDigestV2, RequestCaseDigestV2, opinions_of
from caselens.application.use_cases.write_case_digest import WriteCaseDigest
from caselens.domain.digest import AnswerSentence
from caselens.domain.digest_v2 import DigestBlock, DigestDraft, DigestStage, DigestState, Section
from caselens.domain.errors import AiUnavailableError, CaseNotFoundError
from tests.fakes import (
    FakeJobQueue,
    FakeUnitOfWork,
    InMemoryCaseDigestRepository,
    InMemoryCaseRepository,
    InMemorySubjectRepository,
    ScriptedDigestWriter,
    VerdictChecker,
)
from tests.helpers import parse_digest_case

ERMITA_PARAGRAPH = None  # filled from the real decision below
# A digest is only finished with its core (Doctrine, Facts, Issue, Ruling): the scripted drafts below get backed lines for the parts they leave out.
CORE = {
    Section.DOCTRINE: (DigestBlock((AnswerSentence("The President may not make law by executive order.", ("P132",)),)),),
    Section.FACTS: (DigestBlock((AnswerSentence("The PRC reported the leakage of the nursing exams.", ("P9",)),)),),
    Section.ISSUE: (DigestBlock((AnswerSentence("May the President regulate review centers by order?", ("P132",)),)),),
    Section.RULING: (DigestBlock((AnswerSentence("The petition was granted.", ("P132",)),)),),
}


def with_core(draft: DigestDraft) -> DigestDraft:
    return DigestDraft({**{s: b for s, b in CORE.items() if s not in draft.sections}, **draft.sections})


class World:
    def __init__(self, *, draft=None, writer_error=None, with_writer=True, monthly_limit=0, now=datetime(2026, 10, 15)):
        self.cases, self.digests, self.jobs, self.uow = InMemoryCaseRepository(), InMemoryCaseDigestRepository(), FakeJobQueue(), FakeUnitOfWork()
        self.subjects = InMemorySubjectRepository()
        self.cases.subject_names = {s.id: s.name for s in self.subjects.subjects}
        self.case = self.cases.add(parse_digest_case("gr_180046_2009.html"))
        self.related = parse_digest_case("gr_180046_2009.html")
        self.related.source_url = "https://lawphil.net/other"
        self.related.main_case_id = self.case.id
        self.related = self.cases.add(self.related)
        self.draft = with_core(draft or DigestDraft({}))
        self.writer = ScriptedDigestWriter(self.draft)
        self.checker = VerdictChecker()
        write = WriteCaseDigest(self.writer, self.checker) if with_writer else None
        self.request = RequestCaseDigestV2(self.cases, self.digests, self.jobs, self.uow)
        self.get = GetCaseDigestV2(self.cases, self.digests)
        self._build = BuildCaseDigestV2(self.cases, self.digests, self.uow, write, model="m", prompt_version="v", monthly_limit=monthly_limit, clock=lambda: now)
        if writer_error:
            self.writer.write = lambda request: (_ for _ in ()).throw(writer_error)  # the writer raises

    def build(self, case_id, scope=""):
        """What the worker does for the digest of this case and scope."""
        return self._build.execute(self.digests.get(case_id, scope.lower()).id)


def test_asking_queues_the_job_once_and_asking_again_returns_the_same_digest():
    w = World()
    first, second = w.request.execute(w.case.id), w.request.execute(w.case.id)
    assert first.state is DigestState.PENDING and second.case_id == first.case_id
    assert w.jobs.case_digests == [first.id]  # queued once


def test_a_related_page_is_digested_under_its_main_case():
    w = World()
    digest = w.request.execute(w.related.id)
    assert digest.case_id == w.case.id and w.jobs.case_digests == [digest.id]
    case, found = w.get.execute(w.related.id)
    assert found is digest


def test_an_unknown_case_is_not_found():
    w = World()
    with pytest.raises(CaseNotFoundError):
        w.request.execute(999)
    with pytest.raises(CaseNotFoundError):
        w.get.execute(999)


def test_the_job_writes_the_digest_and_keeps_the_checked_sentences():
    w = World()
    w.request.execute(w.case.id)
    digest = w.build(w.case.id)
    assert digest.state is DigestState.READY and digest.model == "m" and digest.prompt_version == "v"
    assert [s.text for s in digest.draft.sections[Section.FACTS][0].sentences] == ["The PRC reported the leakage of the nursing exams."]
    assert digest.written == 4 and digest.dropped == 0  # the facts line, and the doctrine, issue and ruling every finished digest has


def test_a_digest_says_its_step_while_written_and_none_once_finished():
    w = World()
    asked = w.request.execute(w.case.id)
    assert asked.stage is DigestStage.QUEUED and asked.stage_at is not None
    digest = w.build(w.case.id)
    assert w.digests.stages == [DigestStage.WRITING, DigestStage.CHECKING]  # each step recorded as it began; nothing failed, so no repair
    assert digest.state is DigestState.READY and digest.stage is None and digest.stage_at is None


def test_a_failed_digest_shows_no_step_either():
    w = World(writer_error=AiUnavailableError("down"))
    w.request.execute(w.case.id)
    digest = w.build(w.case.id)
    assert digest.state is DigestState.FAILED and digest.stage is None


def test_a_step_that_cannot_be_recorded_never_stops_the_digest():
    w = World()
    w.digests.set_stage = lambda *args: (_ for _ in ()).throw(RuntimeError("database is locked"))
    w.request.execute(w.case.id)
    assert w.build(w.case.id).state is DigestState.READY


def test_what_the_checks_reject_is_counted_but_never_in_the_digest():
    draft = DigestDraft({Section.FACTS: (DigestBlock((AnswerSentence("Made-up fact.", ("P9",)), AnswerSentence("The PRC reported the leakage.", ("P9",)))),)})
    w = World(draft=draft)
    w.checker.unsupported = {"Made-up fact."}
    w.request.execute(w.case.id)
    digest = w.build(w.case.id)
    assert digest.dropped == 1 and [s.text for s in digest.draft.sections[Section.FACTS][0].sentences] == ["The PRC reported the leakage."]


def test_a_job_that_finds_the_digest_ready_does_not_write_it_again():
    w = World()
    w.request.execute(w.case.id)
    w.build(w.case.id)
    calls = len(w.writer.requests)
    w.build(w.case.id)
    assert len(w.writer.requests) == calls


def test_regenerating_keeps_the_old_text_until_the_new_one_is_ready():
    w = World()
    w.request.execute(w.case.id)
    ready = w.build(w.case.id)
    again = w.request.execute(w.case.id, regenerate=True)
    assert again.state is DigestState.PENDING and again.draft.sections == ready.draft.sections  # still readable while it is rewritten
    assert w.jobs.case_digests == [ready.id, ready.id]


def test_without_an_ai_the_digest_fails_with_a_plain_reason_and_asking_again_retries():
    w = World(with_writer=False)
    w.request.execute(w.case.id)
    digest = w.build(w.case.id)
    assert digest.state is DigestState.FAILED and "No AI key is saved yet" in digest.error and "Settings" in digest.error
    assert w.request.execute(w.case.id).state is DigestState.PENDING  # a failed digest is retried by asking again
    assert len(w.jobs.case_digests) == 2


def test_a_service_that_is_down_fails_the_digest_with_a_plain_reason():
    w = World(writer_error=AiUnavailableError("down"))
    w.request.execute(w.case.id)
    digest = w.build(w.case.id)
    assert digest.state is DigestState.FAILED and "did not answer" in digest.error


def test_over_the_monthly_limit_the_job_stops_before_spending_anything():
    w = World(monthly_limit=1)
    w.digests.started = [datetime(2026, 10, 2), datetime(2026, 10, 9)]  # two started this month, limit one
    w.request.execute(w.case.id)
    digest = w.build(w.case.id)
    assert digest.state is DigestState.FAILED and "limit" in digest.error and w.writer.requests == []


def test_a_digest_started_last_month_does_not_count_against_this_months_limit():
    w = World(monthly_limit=1)
    w.digests.started = [datetime(2026, 9, 28), datetime(2026, 9, 30)]
    w.request.execute(w.case.id)
    assert w.build(w.case.id).state is DigestState.READY


def test_the_students_tags_are_the_digest_topic_and_nothing_guesses_one():
    w = World()
    w.cases.add_subjects(w.case.id, [4, 9], "batch")  # Constitutional Law, Political Law
    w.request.execute(w.case.id)
    w.build(w.case.id)
    assert w.writer.requests[0].subject == "Constitutional Law, Political Law"

    untagged = World()
    untagged.request.execute(untagged.case.id)
    untagged.build(untagged.case.id)
    assert untagged.writer.requests[0].subject is None and untagged.cases.get(untagged.case.id).subjects == ()


def test_a_scope_gets_its_own_digest_and_the_same_scope_asked_again_reuses_it():
    w = World()
    standard = w.request.execute(w.case.id)
    scoped = w.request.execute(w.case.id, "Presidential  powers")
    again = w.request.execute(w.case.id, "presidential powers")  # the same scope, other capitals and spaces
    assert scoped.id != standard.id and again.id == scoped.id and scoped.scope == "Presidential powers"
    assert w.jobs.case_digests == [standard.id, scoped.id]
    w.build(w.case.id, "Presidential powers")
    assert w.writer.requests[0].scope == "Presidential powers"
    assert w.get.execute(w.case.id, "PRESIDENTIAL POWERS")[1].state is DigestState.READY
    assert w.get.execute(w.case.id)[1].state is DigestState.PENDING  # the standard one is its own digest


def test_the_opinions_of_a_decision_are_read_from_the_case():
    case = parse_digest_case("gr_180046_2009.html")
    opinions = opinions_of(case)
    assert [(o.author, o.kind) for o in opinions] == [("BRION", "concurring")] and len(opinions[0].paragraphs) > 5


def test_a_ready_digest_asked_for_again_costs_no_ai_call():
    w = World()
    w.request.execute(w.case.id)
    w.build(w.case.id)
    queued, written = list(w.jobs.case_digests), len(w.writer.requests)
    again = w.request.execute(w.case.id)  # opened again, or the same case in another bulk upload
    assert again.state is DigestState.READY and w.jobs.case_digests == queued and len(w.writer.requests) == written


def test_a_digest_made_by_an_older_prompt_is_served_says_so_and_is_renewed_only_when_asked():
    w = World()
    w.request.execute(w.case.id)
    old = w.build(w.case.id)  # stamped "v" by this world's builder
    assert old.is_current("v") and not old.is_current("v-next")
    served = w.request.execute(w.case.id)  # no surprise spending after an update: still the cached digest
    assert served.id == old.id and served.state is DigestState.READY and len(w.jobs.case_digests) == 1
    renewed = w.request.execute(w.case.id, regenerate=True)
    assert renewed.state is DigestState.PENDING and w.jobs.case_digests == [old.id, old.id]


def test_a_digest_whose_core_the_checks_could_not_back_fails_and_keeps_the_older_text():
    w = World()
    w.request.execute(w.case.id)
    first = w.build(w.case.id)
    w.writer.draft = DigestDraft({Section.FACTS: CORE[Section.FACTS], Section.DOCTRINE: (DigestBlock((AnswerSentence("Made up in 1999.", ("P9",)),)),)})
    w.request.execute(w.case.id, regenerate=True)
    failed = w.build(w.case.id)
    assert failed.state is DigestState.FAILED
    assert "Doctrine, Issue and Ruling" in failed.error and "Try again" in failed.error
    assert failed.draft.sections == first.draft.sections  # the older digest is not replaced by one missing its core
