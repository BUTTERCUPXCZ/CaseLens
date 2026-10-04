"""Requesting, building and editing a digest, on the real decisions of tests/fixtures/digest/.

Expected paragraph numbers come from tests/unit/test_digest_structure.py (read by hand from the pages).
"""
from datetime import datetime

import pytest

from caselens.application.use_cases.answer_case_question import AnswerCaseQuestion
from caselens.application.use_cases.build_case_digest import BuildCaseDigest
from caselens.application.use_cases.edit_digest_field import EditDigestField
from caselens.application.use_cases.request_case_digest import RequestCaseDigest
from caselens.domain.case_digest import (
    DigestStatus,
    DigestTemplate,
    FieldKind,
    FieldOrigin,
    FieldState,
)
from caselens.domain.digest import AnswerSentence
from caselens.domain.errors import AiUnavailableError, DigestNotFoundError, InvalidDigestEditError
from tests.fakes import (
    AlwaysSupported,
    FakeJobQueue,
    FakeUnitOfWork,
    InMemoryCaseRepository,
    InMemoryDigestRepository,
    InMemoryUploadRepository,
    ScriptedWriter,
)
from tests.helpers import parse_digest_case

REAL = "gr_180046_2009.html"  # has The Facts / The Issues headings
NO_HEADINGS = "gr_173931_2009.html"  # the Court wrote none


class Setup:
    def __init__(self, decision: str = REAL, writer: ScriptedWriter | None = None, *, with_ai: bool = True, allowed: bool = True):
        self.cases, self.digests, self.jobs = InMemoryCaseRepository(), InMemoryDigestRepository(), FakeJobQueue()
        self.uploads, self.uow = InMemoryUploadRepository(), FakeUnitOfWork()
        self.case = self.cases.add(parse_digest_case(decision))
        self.writer = writer or ScriptedWriter([AnswerSentence("The Court declared the order void.", ("P132",))])
        answerer = AnswerCaseQuestion(self.writer, AlwaysSupported()) if with_ai else None
        self.request = RequestCaseDigest(self.cases, self.digests, self.jobs, self.uow)
        self.build = BuildCaseDigest(
            self.cases, self.digests, self.uploads, self.uow, answerer,
            model="m", prompt_version="v", ai_allowed=lambda: allowed, clock=lambda: datetime(2026, 10, 4),
        )
        self.edit = EditDigestField(self.cases, self.digests, self.jobs, self.uow)


class TestRequesting:
    def test_the_courts_own_text_is_filled_in_at_once_and_the_answers_are_queued(self):
        s = Setup()
        digest = s.request.execute(s.case.id)

        facts, issues, ruling = (digest.field_named(k) for k in ("facts", "issues", "ruling"))
        assert (facts.passage.first, facts.origin) == (9, FieldOrigin.COURT_HEADING)
        assert facts.text.startswith("On 11 and 12 June 2006, the Professional Regulation Commission")
        assert (issues.passage.first, issues.passage.last) == (64, 66)
        assert ruling.origin is FieldOrigin.COURT_RULING and ruling.text.startswith("WHEREFORE, we GRANT the petition")
        assert digest.field_named("doctrine").origin is FieldOrigin.EMPTY  # never guessed
        assert digest.status is DigestStatus.PENDING
        assert [f.state for f in digest.fields if f.kind is FieldKind.ANSWER] == [FieldState.PENDING] * 2
        assert s.jobs.digest_builds == [(digest.id, None)]

    def test_a_long_court_section_is_cut_and_says_so(self):
        facts = Setup().request.execute(1).field_named("facts")
        assert (facts.passage.first, facts.passage.last) == (9, 12)  # the Court's section is paragraphs 9-62
        assert facts.note == "Showing the first 4 of 54 paragraphs. Pick the passage you want."

    def test_no_heading_means_an_empty_field_with_a_plain_reason_not_a_guess(self):
        s = Setup(NO_HEADINGS)
        digest = s.request.execute(s.case.id)
        facts = digest.field_named("facts")
        assert facts.text == "" and facts.origin is FieldOrigin.EMPTY
        assert facts.note.startswith("The Court did not label the facts in this decision.")
        assert digest.field_named("ruling").text.startswith("WHEREFORE, the petition is DENIED")  # always found

    def test_asking_twice_returns_the_same_digest_and_queues_the_ai_once(self):
        s = Setup()
        first, second = s.request.execute(s.case.id), s.request.execute(s.case.id)
        assert first.id == second.id and len(s.jobs.digest_builds) == 1

    def test_the_same_case_in_two_reviews_gets_two_digests(self):
        s = Setup()
        assert s.request.execute(s.case.id, upload_id=1).id != s.request.execute(s.case.id, upload_id=2).id

    def test_the_short_template_needs_no_ai_and_is_ready_immediately(self):
        s = Setup()
        digest = s.request.execute(s.case.id, template=DigestTemplate.FACTS_AND_DOCTRINE)
        assert [f.key for f in digest.fields] == ["facts", "doctrine"]
        assert digest.status is DigestStatus.READY and s.jobs.digest_builds == []

    def test_questions_of_the_students_own_become_answer_fields(self):
        s = Setup()
        digest = s.request.execute(s.case.id, questions=["Give 4 sentences of the facts in layman terms."])
        custom = digest.field_named("q1")
        assert custom.kind is FieldKind.ANSWER and custom.state is FieldState.PENDING
        assert custom.question == "Give 4 sentences of the facts in layman terms."

    def test_an_unknown_case_is_refused(self):
        with pytest.raises(Exception, match="does not exist"):
            Setup().request.execute(999)

    def test_a_failed_digest_is_retried_by_asking_again(self):
        s = Setup()
        digest = s.request.execute(s.case.id)
        digest.status, digest.error = DigestStatus.FAILED, "boom"
        s.request.execute(s.case.id)
        assert digest.status is DigestStatus.PENDING and len(s.jobs.digest_builds) == 2


class TestBuilding:
    def test_answers_are_written_into_their_fields_with_their_sources(self):
        s = Setup()
        digest = s.request.execute(s.case.id)
        s.build.execute(digest.id)

        topic = s.digests.get(digest.id).field_named("topic")
        assert (topic.state, topic.origin) == (FieldState.READY, FieldOrigin.AI_DRAFTED)
        assert topic.text == "The Court declared the order void." and topic.cites == ("P132",)
        done = s.digests.get(digest.id)
        assert done.status is DigestStatus.READY and done.model == "m" and done.ai_answered_at == datetime(2026, 10, 4)

    def test_the_answer_is_asked_with_the_decision_body_and_not_the_caption_or_signatures(self):
        s = Setup()
        digest = s.request.execute(s.case.id)
        s.build.execute(digest.id)
        ids = [source.id for source in s.writer.requests[0].sources]
        assert ids[0] == "P6" and ids[-1] == "P132" and "P5" not in ids and "P133" not in ids  # P5 = ponente line, P133 = SO ORDERED

    def test_progress_is_saved_after_each_answer_so_the_student_sees_it_appear(self):
        s = Setup()
        digest = s.request.execute(s.case.id)
        before = s.uow.commits
        s.build.execute(digest.id)
        assert s.uow.commits - before >= 3  # one per answer and a final one

    def test_without_an_ai_key_the_digest_still_works_and_says_why(self):
        s = Setup(with_ai=False)
        digest = s.request.execute(s.case.id)
        s.build.execute(digest.id)
        done = s.digests.get(digest.id)
        topic = done.field_named("topic")
        assert topic.state is FieldState.UNAVAILABLE and topic.note == "Written explanations are not set up on this server."
        assert done.status is DigestStatus.READY and done.field_named("ruling").text  # the Court's text is untouched

    def test_when_the_ai_service_is_down_the_field_says_so_and_nothing_is_invented(self):
        s = Setup(writer=ScriptedWriter(error=AiUnavailableError("down")))
        digest = s.request.execute(s.case.id)
        s.build.execute(digest.id)
        topic = s.digests.get(digest.id).field_named("topic")
        assert topic.state is FieldState.UNAVAILABLE and topic.text == ""
        assert topic.note == "The explanation service did not answer. Try again in a moment."

    def test_over_the_daily_limit_nothing_is_sent_to_the_ai(self):
        s = Setup(allowed=False)
        digest = s.request.execute(s.case.id)
        s.build.execute(digest.id)
        assert s.writer.requests == []
        assert "limit" in s.digests.get(digest.id).field_named("why").note

    def test_when_the_decision_does_not_say_enough_the_field_is_left_empty(self):
        s = Setup(writer=ScriptedWriter([]))
        digest = s.request.execute(s.case.id)
        s.build.execute(digest.id)
        why = s.digests.get(digest.id).field_named("why")
        assert why.state is FieldState.UNAVAILABLE and why.note.startswith("The decision does not say enough")

    def test_building_twice_does_not_pay_for_the_same_answers_again(self):
        s = Setup()
        digest = s.request.execute(s.case.id)
        s.build.execute(digest.id)
        asked = len(s.writer.requests)
        s.build.execute(digest.id)
        assert len(s.writer.requests) == asked

    def test_only_the_named_question_is_written_again(self):
        s = Setup()
        digest = s.request.execute(s.case.id)
        s.build.execute(digest.id)
        asked = len(s.writer.requests)
        s.build.execute(digest.id, ["why"])
        assert len(s.writer.requests) == asked + 1

    def test_text_the_student_pasted_is_given_to_the_answer_as_a_source(self):
        s = Setup()
        digest = s.request.execute(s.case.id)
        s.edit.paste_text(digest.id, "doctrine", "Plenary power is vested in Congress.")
        s.build.execute(digest.id)
        sources = {x.id: x.text for x in s.writer.requests[0].sources}
        assert sources["S1"] == "Plenary power is vested in Congress."

    def test_a_missing_digest_is_reported(self):
        with pytest.raises(DigestNotFoundError):
            Setup().build.execute(404)


class TestEditing:
    def build(self):
        s = Setup()
        digest = s.request.execute(s.case.id)
        s.build.execute(digest.id)
        return s, digest.id

    def test_typing_over_a_field_marks_it_as_the_students_and_keeps_the_original(self):
        s, id_ = self.build()
        s.edit.write_text(id_, "ruling", "My own words.")
        ruling = s.digests.get(id_).field_named("ruling")
        assert (ruling.text, ruling.origin, ruling.edited) == ("My own words.", FieldOrigin.STUDENT_WRITTEN, True)
        assert ruling.original.text.startswith("WHEREFORE, we GRANT the petition")

    def test_reset_puts_the_courts_text_back(self):
        s, id_ = self.build()
        s.edit.write_text(id_, "ruling", "My own words.")
        s.edit.write_text(id_, "ruling", "Edited twice.")  # the original survives a second edit
        s.edit.reset(id_, "ruling")
        ruling = s.digests.get(id_).field_named("ruling")
        assert ruling.origin is FieldOrigin.COURT_RULING and not ruling.edited and ruling.text.startswith("WHEREFORE")

    def test_picking_paragraphs_takes_the_courts_exact_words_from_the_stored_decision(self):
        s, id_ = self.build()
        s.edit.pick_passage(id_, "doctrine", 109, 109)
        doctrine = s.digests.get(id_).field_named("doctrine")
        assert doctrine.origin is FieldOrigin.STUDENT_PICKED
        assert doctrine.text == s.case.full_text.split("\n")[109]
        assert (doctrine.passage.first, doctrine.passage.last) == (109, 109)

    @pytest.mark.parametrize(("first", "last"), [(0, 3), (5, 9), (10, 5), (130, 140), (9, 60)])
    def test_a_passage_outside_the_body_of_the_decision_or_too_long_is_refused(self, first, last):
        s, id_ = self.build()
        with pytest.raises(InvalidDigestEditError):
            s.edit.pick_passage(id_, "doctrine", first, last)

    def test_pasted_text_is_marked_as_pasted(self):
        s, id_ = self.build()
        s.edit.paste_text(id_, "doctrine", "Pasted rule.")
        assert s.digests.get(id_).field_named("doctrine").origin is FieldOrigin.STUDENT_PASTED

    def test_an_answer_field_cannot_be_filled_by_picking_paragraphs(self):
        s, id_ = self.build()
        with pytest.raises(InvalidDigestEditError, match="written from the decision"):
            s.edit.pick_passage(id_, "topic", 20, 21)

    def test_an_unknown_field_is_refused(self):
        s, id_ = self.build()
        with pytest.raises(InvalidDigestEditError, match="no field"):
            s.edit.write_text(id_, "nonsense", "x")

    def test_asking_a_new_question_adds_a_pending_field_and_queues_it(self):
        s, id_ = self.build()
        s.edit.ask(id_, "Is EO 566 valid?")
        added = s.digests.get(id_).field_named("q1")
        assert added.state is FieldState.PENDING and added.question == "Is EO 566 valid?"
        assert s.jobs.digest_builds[-1] == (id_, ["q1"])
        s.edit.ask(id_, "Another one?")
        assert s.digests.get(id_).field_named("q2") is not None

    @pytest.mark.parametrize("question", ["", "   ", "x" * 301])
    def test_an_empty_or_huge_question_is_refused(self, question):
        s, id_ = self.build()
        with pytest.raises(InvalidDigestEditError):
            s.edit.ask(id_, question)

    def test_only_answer_fields_can_be_regenerated(self):
        s, id_ = self.build()
        s.edit.regenerate(id_, ["why"])
        with pytest.raises(InvalidDigestEditError):
            s.edit.regenerate(id_, ["ruling"])


class TestCheckNote:
    def test_a_whole_sentence_taken_as_the_title_is_not_shown_as_a_title_mismatch(self):
        from caselens.application.use_cases.build_finished_reviewer import _check_note
        from caselens.domain.entities import UploadedCitation
        from caselens.domain.value_objects import ClaimedCitation, GrNumber

        citation = UploadedCitation(ClaimedCitation(GrNumber("180046"), "GR no 180046"))
        citation.mismatches = {
            "year": {"claimed": "2010", "official": "2009"},
            "title": {"claimed": "Section 1: " + "the legislative power shall be vested in Congress " * 5, "official": "Review Center"},
        }
        note = _check_note(citation)
        assert note == "Check this citation. year: your reviewer says 2010; the Court's record says 2009."

    def test_a_real_short_title_difference_is_still_shown(self):
        from caselens.application.use_cases.build_finished_reviewer import _check_note
        from caselens.domain.entities import UploadedCitation
        from caselens.domain.value_objects import ClaimedCitation, GrNumber

        citation = UploadedCitation(ClaimedCitation(GrNumber("180046"), "GR no 180046"))
        citation.mismatches = {"title": {"claimed": "Review Center v Ermita", "official": "Review Center Association vs. Ermita"}}
        assert "Review Center v Ermita" in _check_note(citation)


class TestParallelAnswers:
    def test_the_answers_of_one_digest_are_written_side_by_side_so_two_take_about_as_long_as_one(self):
        import time

        class SlowWriter(ScriptedWriter):
            def write(self, request):
                time.sleep(0.4)
                return super().write(request)

        s = Setup(writer=SlowWriter([AnswerSentence("The Court declared the order void.", ("P132",))]))
        digest = s.request.execute(s.case.id)  # topic and why
        started = time.perf_counter()
        s.build.execute(digest.id)
        took = time.perf_counter() - started
        assert took < 0.7  # two 0.4 s answers one after the other would take 0.8 s
        done = s.digests.get(digest.id)
        assert done.field_named("topic").state is FieldState.READY and done.field_named("why").state is FieldState.READY

    def test_each_answer_is_still_saved_as_soon_as_it_is_ready(self):
        s = Setup()
        digest = s.request.execute(s.case.id)
        before = s.uow.commits
        s.build.execute(digest.id)
        assert s.uow.commits - before >= 3  # one per answer, and the final one

    def test_one_answer_failing_does_not_lose_the_other(self):
        class FlakyWriter(ScriptedWriter):
            def write(self, request):
                if "Why does this case matter" in request.question:
                    raise AiUnavailableError("down")
                return super().write(request)

        s = Setup(writer=FlakyWriter([AnswerSentence("The Court declared the order void.", ("P132",))]))
        digest = s.request.execute(s.case.id)
        s.build.execute(digest.id)
        done = s.digests.get(digest.id)
        assert done.field_named("topic").state is FieldState.READY
        assert done.field_named("why").state is FieldState.UNAVAILABLE and done.field_named("why").note.startswith("The explanation service did not answer")
