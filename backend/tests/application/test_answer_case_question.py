from caselens.application.ports.ai import AnswerChecker, AnswerRequest, AnswerWriter
from caselens.application.use_cases.answer_case_question import AnswerCaseQuestion, decision_sources
from caselens.domain.digest import AnswerSentence, CheckResult, SourcePassage, Verdict

SOURCES = (
    SourcePassage("P1", "The Court held that Executive Order No. 566 is invalid."),
    SourcePassage("P2", "Only Congress may make laws."),
)


class FakeWriter(AnswerWriter):
    def __init__(self, sentences):
        self.sentences, self.requests = sentences, []

    def write(self, request):
        self.requests.append(request)
        return self.sentences


class FakeChecker(AnswerChecker):
    def __init__(self, verdicts):
        self.verdicts, self.calls = verdicts, 0

    def check(self, sentences, sources):
        self.calls += 1
        return [CheckResult(self.verdicts[s.text], "because") for s in sentences]


def answer(sentences, verdicts=None):
    checker = FakeChecker(verdicts or {})
    result = AnswerCaseQuestion(FakeWriter(sentences), checker).answer(AnswerRequest("Why does it matter?", SOURCES))
    return result, checker


def test_a_supported_sentence_is_kept():
    s = AnswerSentence("The Court held that EO 566 is invalid.", ("P1",))
    result, _ = answer([s], {s.text: Verdict.SUPPORTED})
    assert result.sentences == (s,) and not result.abstained and result.dropped == ()


def test_a_sentence_the_checker_does_not_fully_support_is_dropped_and_explained():
    good = AnswerSentence("Only Congress may make laws.", ("P2",))
    weak = AnswerSentence("The Court held that EO 566 is invalid.", ("P1",))
    result, _ = answer([good, weak], {good.text: Verdict.SUPPORTED, weak.text: Verdict.PARTLY})
    assert result.sentences == (good,)
    assert [d.reason for d in result.dropped] == ["checker: partly_supported (because)"]


def test_a_sentence_failing_the_code_checks_never_reaches_the_checker():
    invented = AnswerSentence("The Court awarded P9,000,000.", ("P1",))
    result, checker = answer([invented])
    assert result.abstained
    assert result.dropped[0].reason == "number 9,000,000 is not in the cited text"
    assert checker.calls == 0


def test_when_nothing_survives_the_answer_is_empty_not_a_guess():
    s = AnswerSentence("The Court held that EO 566 is invalid.", ("P1",))
    result, _ = answer([s], {s.text: Verdict.NOT_SUPPORTED})
    assert result.abstained and result.sentences == ()


def test_an_empty_draft_is_an_empty_answer_and_the_checker_is_not_called():
    result, checker = answer([])
    assert result.abstained and checker.calls == 0


def test_the_answer_is_cut_to_the_requested_length():
    sentences = [AnswerSentence(f"Only Congress may make laws{'!' * i}.", ("P2",)) for i in range(5)]
    verdicts = {s.text: Verdict.SUPPORTED for s in sentences}
    writer, checker = FakeWriter(sentences), FakeChecker(verdicts)
    result = AnswerCaseQuestion(writer, checker).answer(AnswerRequest("q", SOURCES, max_sentences=2))
    assert len(result.sentences) == 2


def test_decision_sources_are_numbered_by_their_position_in_the_stored_text():
    sources = decision_sources(["a", "b", "c", "d"], 1, 2)
    assert [(s.id, s.text) for s in sources] == [("P1", "b"), ("P2", "c")]


def test_a_very_long_paragraph_is_shortened_but_keeps_its_id():
    sources = decision_sources(["x" * 5000], 0, 0, max_chars=100)
    assert sources[0].id == "P0" and len(sources[0].text) < 110
