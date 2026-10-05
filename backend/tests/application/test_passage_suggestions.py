"""The AI that only points at where the Court states the Facts, Issue or Doctrine, on the real decisions of
tests/fixtures/digest/. The AI is a script here; what is tested is everything around it: the code checks, that the text
is copied from the stored decision (never from the AI), and that anything doubtful leaves the box empty."""
from datetime import datetime

import pytest

from caselens.application.use_cases.answer_case_question import AnswerCaseQuestion
from caselens.application.use_cases.build_case_digest import BuildCaseDigest
from caselens.application.use_cases.edit_digest_field import EditDigestField
from caselens.application.use_cases.request_case_digest import RequestCaseDigest
from caselens.application.use_cases.suggest_court_passages import PICKED_BY_AI, SuggestCourtPassages
from caselens.domain.case_digest import DigestStatus, FieldOrigin, FieldState
from caselens.domain.digest import AnswerSentence, ParagraphRange, Verdict
from caselens.domain.errors import AiUnavailableError, InvalidDigestEditError
from caselens.domain.services.digest_field_factory import DigestFieldFactory
from caselens.domain.services.heading_sections import HeadingSections
from caselens.domain.services.ruling_locator import RulingLocator
from tests.fakes import (
    AlwaysSupported,
    FakeJobQueue,
    FakeUnitOfWork,
    InMemoryCaseRepository,
    InMemoryDigestRepository,
    InMemoryUploadRepository,
    ScriptedPassageChecker,
    ScriptedPicker,
    ScriptedWriter,
)
from tests.helpers import digest_paragraphs, parse_digest_case

NO_HEADINGS = "gr_173931_2009.html"  # the Court wrote no heading and no recognisable statement of the issue; ruling at 53
PARAGRAPHS = digest_paragraphs(NO_HEADINGS)
START, RULING = HeadingSections.body_start(PARAGRAPHS), RulingLocator().locate(PARAGRAPHS)


def use_case(picks, verdicts=None, silent=False, error=None):
    picker, checker = ScriptedPicker(picks, error), ScriptedPassageChecker(verdicts, silent)
    return SuggestCourtPassages(picker, checker), picker, checker


class TestTheUseCase:
    def test_a_confirmed_pick_is_copied_from_the_stored_decision(self):
        case, _, checker = use_case({"facts": (8, 12), "issues": (23, 23)})
        result = case.execute(["facts", "issues"], PARAGRAPHS, START, RULING)
        assert result.found["facts"].range == ParagraphRange(8, 12) and result.found["facts"].reason == PICKED_BY_AI
        assert result.found["issues"].range == ParagraphRange(23, 23)
        # what the second check read is the Court's own text, not anything the AI wrote
        assert checker.seen[0]["issues"] == PARAGRAPHS[23]

    def test_a_pick_outside_the_body_of_the_decision_is_refused(self):
        case, _, checker = use_case({"issues": (1, 3)})  # the caption
        result = case.execute(["issues"], PARAGRAPHS, START, RULING)
        assert "issues" not in result.found and "outside the body" in result.not_found["issues"]
        assert checker.seen == []  # an impossible pick never reaches the second model

    def test_a_pick_that_runs_into_the_ruling_is_refused(self):
        case, *_ = use_case({"facts": (START, RULING.first)})
        assert "outside the body" in case.execute(["facts"], PARAGRAPHS, START, RULING).not_found["facts"]

    def test_too_many_paragraphs_for_the_part_is_refused(self):
        case, *_ = use_case({"doctrine": (10, 20)})
        assert "more than" in case.execute(["doctrine"], PARAGRAPHS, START, RULING).not_found["doctrine"]

    def test_null_means_the_decision_does_not_state_it(self):
        case, *_ = use_case({})
        result = case.execute(["issues"], PARAGRAPHS, START, RULING)
        assert result.found == {} and "does not state it" in result.not_found["issues"]

    @pytest.mark.parametrize("verdict", [Verdict.PARTLY, Verdict.NOT_SUPPORTED])
    def test_the_second_model_must_say_yes(self, verdict):
        case, *_ = use_case({"issues": (23, 23)}, {"issues": verdict})
        result = case.execute(["issues"], PARAGRAPHS, START, RULING)
        assert result.found == {} and "second check did not agree" in result.not_found["issues"]

    def test_silence_from_the_second_model_is_not_approval(self):
        case, *_ = use_case({"issues": (23, 23)}, silent=True)
        assert use_case({"issues": (23, 23)}, silent=True)[0].execute(["issues"], PARAGRAPHS, START, RULING).found == {}

    def test_each_part_is_judged_on_its_own(self):
        case, *_ = use_case({"facts": (8, 12), "issues": (23, 23)}, {"issues": Verdict.NOT_SUPPORTED})
        result = case.execute(["facts", "issues"], PARAGRAPHS, START, RULING)
        assert set(result.found) == {"facts"} and "issues" in result.not_found

    def test_the_ai_is_only_offered_the_body_and_a_window_for_facts_and_issue(self):
        case, picker, _ = use_case({})
        case.execute(["facts", "doctrine"], PARAGRAPHS, START, RULING)
        offered = {key: [p.id for p in passages] for key, passages in picker.requests[0].candidates.items()}
        assert offered["facts"][0] == f"P{START}" and offered["facts"][-1] == f"P{RULING.first - 1}"
        assert "P0" not in offered["facts"] and f"P{RULING.first}" not in offered["doctrine"]

    def test_a_service_that_is_down_raises_for_the_caller_to_settle(self):
        case, *_ = use_case({}, error=AiUnavailableError("down"))
        with pytest.raises(AiUnavailableError):
            case.execute(["facts"], PARAGRAPHS, START, RULING)

    def test_a_decision_with_no_readable_body_suggests_nothing_and_asks_nothing(self):
        case, picker, _ = use_case({"facts": (1, 2)})
        result = case.execute(["facts"], PARAGRAPHS, None, None)
        assert result.found == {} and picker.requests == []


class Setup:
    def __init__(self, picks=None, verdicts=None, *, error=None, allowed=True, with_suggester=True):
        self.cases, self.digests, self.jobs = InMemoryCaseRepository(), InMemoryDigestRepository(), FakeJobQueue()
        self.uploads, self.uow = InMemoryUploadRepository(), FakeUnitOfWork()
        self.case = self.cases.add(parse_digest_case(NO_HEADINGS))
        self.picker, self.checker = ScriptedPicker(picks, error), ScriptedPassageChecker(verdicts)
        suggester = SuggestCourtPassages(self.picker, self.checker) if with_suggester else None
        self.request = RequestCaseDigest(self.cases, self.digests, self.jobs, self.uow, DigestFieldFactory(look_for_passages=with_suggester))
        answerer = AnswerCaseQuestion(ScriptedWriter([AnswerSentence("The Court declared the order void.", ("P40",))]), AlwaysSupported())
        self.build = BuildCaseDigest(
            self.cases, self.digests, self.uploads, self.uow, answerer, model="m", prompt_version="v",
            ai_allowed=lambda: allowed, clock=lambda: datetime(2026, 10, 5), suggester=suggester,
        )
        self.edit = EditDigestField(self.cases, self.digests, self.jobs, self.uow)


class TestInTheDigest:
    def test_missing_parts_start_as_being_looked_for_and_the_job_is_queued(self):
        s = Setup()
        digest = s.request.execute(s.case.id)
        assert [digest.field_named(k).state for k in ("facts", "issues", "doctrine")] == [FieldState.PENDING] * 3
        assert digest.status is DigestStatus.PENDING and s.jobs.digest_builds == [(digest.id, None)]

    def test_the_picked_paragraphs_fill_the_boxes_as_the_courts_words_marked_as_suggestions(self):
        s = Setup({"facts": (8, 12), "issues": (23, 23), "doctrine": (30, 30)})
        digest = s.request.execute(s.case.id)
        s.build.execute(digest.id)
        facts, issues, doctrine = (digest.field_named(k) for k in ("facts", "issues", "doctrine"))
        assert all(f.origin is FieldOrigin.COURT_SUGGESTED and f.state is FieldState.READY for f in (facts, issues, doctrine))
        assert issues.text == PARAGRAPHS[23] and (issues.passage.first, issues.passage.last) == (23, 23)
        assert facts.text == "\n\n".join(PARAGRAPHS[8:12])  # the first 4 of 5, with the usual note
        assert facts.note == "Showing the first 4 of 5 paragraphs. Pick the passage you want."
        assert issues.reason == PICKED_BY_AI
        assert digest.ai_answered_at == datetime(2026, 10, 5) and digest.status is DigestStatus.READY

    def test_the_explanations_are_still_written_beside_it(self):
        s = Setup({"issues": (23, 23)})
        digest = s.request.execute(s.case.id)
        s.build.execute(digest.id)
        assert digest.field_named("topic").state is FieldState.READY and digest.field_named("topic").text

    def test_what_the_ai_could_not_confirm_is_left_empty_with_a_plain_reason(self):
        s = Setup({"issues": (23, 23), "facts": (8, 12)}, {"issues": Verdict.PARTLY})
        digest = s.request.execute(s.case.id)
        s.build.execute(digest.id)
        issues = digest.field_named("issues")
        assert issues.origin is FieldOrigin.EMPTY and issues.state is FieldState.READY and issues.text == ""
        assert issues.note.startswith("We did not find where the Court states the issue")
        assert digest.field_named("facts").origin is FieldOrigin.COURT_SUGGESTED

    def test_a_service_that_is_down_says_so_and_offers_to_try_again(self):
        s = Setup(error=AiUnavailableError("down"))
        digest = s.request.execute(s.case.id)
        s.build.execute(digest.id)
        assert "Suggest for me" in digest.field_named("issues").note and digest.field_named("issues").state is FieldState.READY
        assert digest.status is DigestStatus.READY

    def test_over_the_daily_limit_nothing_is_asked_and_the_student_is_told(self):
        s = Setup({"issues": (23, 23)}, allowed=False)
        digest = s.request.execute(s.case.id)
        s.build.execute(digest.id)
        assert s.picker.requests == [] and "limit for suggestions today" in digest.field_named("issues").note

    def test_with_no_ai_set_up_the_digest_never_waits_for_a_look(self):
        s = Setup(with_suggester=False)
        digest = s.request.execute(s.case.id)
        assert [digest.field_named(k).state for k in ("facts", "issues", "doctrine")] == [FieldState.READY] * 3
        assert digest.field_named("issues").note.startswith("The Court did not label the issue")

    def test_suggest_for_me_looks_again_only_at_an_empty_part(self):
        s = Setup({"issues": (23, 23)}, {"issues": Verdict.NOT_SUPPORTED})
        digest = s.request.execute(s.case.id)
        s.build.execute(digest.id)  # not confirmed: the box is empty
        s.jobs.digest_builds.clear()

        s.edit.suggest(digest.id, "issues")
        assert digest.field_named("issues").state is FieldState.PENDING
        assert s.jobs.digest_builds == [(digest.id, ["issues"])]

        s.checker.verdicts["issues"] = Verdict.SUPPORTED
        s.build.execute(digest.id, ["issues"])
        assert digest.field_named("issues").origin is FieldOrigin.COURT_SUGGESTED

    def test_suggest_for_me_never_replaces_a_student_pick_or_an_existing_suggestion(self):
        s = Setup({"issues": (23, 23)})
        digest = s.request.execute(s.case.id)
        s.build.execute(digest.id)
        with pytest.raises(InvalidDigestEditError):
            s.edit.suggest(digest.id, "issues")  # already has text
        s.edit.pick_passage(digest.id, "doctrine", 30, 30)
        with pytest.raises(InvalidDigestEditError):
            s.edit.suggest(digest.id, "doctrine")  # the student's own pick
        with pytest.raises(InvalidDigestEditError):
            s.edit.suggest(digest.id, "ruling")  # not a part we look for

    def test_putting_back_the_systems_version_restores_the_suggestion(self):
        s = Setup({"issues": (23, 23)})
        digest = s.request.execute(s.case.id)
        s.build.execute(digest.id)
        s.edit.write_text(digest.id, "issues", "My own wording")
        s.edit.reset(digest.id, "issues")
        restored = digest.field_named("issues")
        assert restored.origin is FieldOrigin.COURT_SUGGESTED and restored.text == PARAGRAPHS[23]


class TestTheRulesFillTheIssueWithoutAnyAi:
    def test_an_issue_the_court_states_in_its_own_words_is_suggested_instantly(self):
        cases, digests = InMemoryCaseRepository(), InMemoryDigestRepository()
        case = cases.add(parse_digest_case("gr_117246_1995.html"))  # no heading; "The petition before us raises the following contentions"
        digest = RequestCaseDigest(cases, digests, FakeJobQueue(), FakeUnitOfWork()).execute(case.id)
        issue = digest.field_named("issues")
        assert issue.origin is FieldOrigin.COURT_SUGGESTED and issue.state is FieldState.READY
        assert (issue.passage.first, issue.passage.last) == (13, 16) and issue.reason.startswith("cue:")
        assert issue.text.startswith("The petition before us raises the following contentions")

    def test_a_decision_that_states_no_issue_gets_none_from_the_rules(self):
        cases, digests = InMemoryCaseRepository(), InMemoryDigestRepository()
        case = cases.add(parse_digest_case("gr_37012_1992.html"))  # hand-marked: the Court states no issue
        issue = RequestCaseDigest(cases, digests, FakeJobQueue(), FakeUnitOfWork()).execute(case.id).field_named("issues")
        assert issue.origin is FieldOrigin.EMPTY and issue.text == ""


class TestInTheWordFile:
    def test_a_suggested_passage_is_labelled_and_a_pending_one_says_it_is_being_looked_for(self):
        from caselens.application.use_cases.build_finished_reviewer import _box_field
        from caselens.domain.case_digest import DigestField, FieldKind

        suggested = DigestField("issues", "Issue", FieldKind.VERBATIM, "The issue is whether...", FieldOrigin.COURT_SUGGESTED)
        assert _box_field(suggested).note == "The Court's own words, suggested from the decision: check it."
        looking = DigestField("facts", "Facts", FieldKind.VERBATIM, state=FieldState.PENDING)
        assert _box_field(looking).note == "Still looking for the Court's passage."


class TestTidyingTheFacts:
    def case(self, paragraphs):
        picker = ScriptedPicker({"facts": (1, len(paragraphs) - 2)})
        return SuggestCourtPassages(picker, ScriptedPassageChecker()), paragraphs

    def run(self, paragraphs):
        use_case_, paragraphs = self.case(paragraphs)
        return use_case_.execute(["facts"], paragraphs, 1, ParagraphRange(len(paragraphs) - 1, len(paragraphs) - 1)).found["facts"].range

    def test_the_opening_line_that_only_announces_the_petition_is_left_out(self):
        paragraphs = ["x", "Challenged in this Petition for Review on Certiorari are the February 2006 Decision and May 2006 Resolution of the Court of Appeals.", "The facts are uncomplicated. Petitioner is a labor union.", "On December 13, 2001, the board resolved to close the restaurant.", "SO ORDERED."]
        assert self.run(paragraphs) == ParagraphRange(2, 3)

    def test_a_real_first_fact_is_never_dropped_as_an_introduction(self):
        paragraphs = ["x", "The instant case stems from a Complaint for Specific Performance filed by the buyers in 2001.", "On December 13, 2001, the board resolved to close the restaurant.", "SO ORDERED."]
        assert self.run(paragraphs) == ParagraphRange(1, 2)

    def test_the_facts_stop_where_the_partys_argument_begins(self):
        paragraphs = ["x", "Canete claimed that she was a regular worker and filed a complaint.", "Both the Arbiter and the NLRC agreed with Canete.", "In the instant petition, petitioner Company contends that the Labor Tribunal committed grave abuse of discretion.", "The Court finds the petition without merit.", "SO ORDERED."]
        assert self.run(paragraphs) == ParagraphRange(1, 2)
