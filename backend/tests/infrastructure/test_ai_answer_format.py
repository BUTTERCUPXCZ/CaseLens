"""The digest writer and the checker answer in a short format (short field names; a reason only for a rejected sentence), because output
tokens are what a digest costs. The older, longer answer is still read, so nothing is lost if a model answers that way."""
from caselens.application.ports.ai import DigestRequest
from caselens.domain.digest import AnswerSentence, SourcePassage, Verdict
from caselens.domain.digest_v2 import Section
from caselens.infrastructure.ai.gemini_answerer import GeminiAnswerChecker
from caselens.infrastructure.ai.gemini_digest import GeminiDigestWriter
from caselens.infrastructure.config import Settings


class Call:
    """Answers with what it was given, and keeps the requests."""

    def __init__(self, answer):
        self.answer, self.asked, self.provider, self.usage = answer, [], "test", {}

    def json(self, model, system, prompt, schema, *, thinking_budget=None):
        self.asked.append((model, system, schema))
        return self.answer

    def model_for(self, role):
        return role


REQUEST = DigestRequest((SourcePassage("P6", "Marcos was deposed in 1986."),), "Marcos v. Manglapus, G.R. No. 88211")


def write(answer):
    return GeminiDigestWriter(Settings(), Call(answer)).write(REQUEST)


def test_the_writer_reads_the_short_format():
    draft = write({"facts": [{"s": [{"t": "Marcos was deposed.", "c": ["P6"], "k": True}, {"t": "He left.", "c": ["P6"]}]}],
                   "why": [{"h": "Remember", "l": True, "s": [{"t": "A point.", "c": ["P6"]}]}]})
    facts, why = draft.sections[Section.FACTS][0], draft.sections[Section.WHY][0]
    assert [(s.text, s.cites, s.key) for s in facts.sentences] == [("Marcos was deposed.", ("P6",), True), ("He left.", ("P6",), False)]
    assert not facts.as_list and facts.heading is None and why.as_list and why.heading == "Remember"


def test_the_writer_still_reads_the_older_long_format():
    draft = write({"facts": [{"heading": None, "kind": "list", "sentences": [{"text": "Marcos was deposed.", "cites": ["P6"], "key": True}]}]})
    block = draft.sections[Section.FACTS][0]
    assert block.as_list and block.sentences[0] == AnswerSentence("Marcos was deposed.", ("P6",), True)


def test_the_writer_asks_for_the_short_format():
    call = Call({})
    GeminiDigestWriter(Settings(), call).write(REQUEST)
    _, system, schema = call.asked[0]
    sentence = schema["properties"]["facts"]["items"]["properties"]["s"]["items"]
    assert set(sentence["properties"]) == {"t", "c", "k"} and "compact JSON" in system


def test_the_checker_reads_short_verdicts_and_needs_a_reason_only_for_a_rejection():
    sources = {"P6": SourcePassage("P6", "Marcos was deposed in 1986.")}
    sentences = [AnswerSentence("Marcos was deposed.", ("P6",)), AnswerSentence("Marcos was crowned.", ("P6",))]
    call = Call({"verdicts": [{"i": 0, "v": "supported"}, {"i": 1, "v": "not_supported", "r": "P6 says deposed"}]})
    results = GeminiAnswerChecker(Settings(), call).check(sentences, sources)
    assert [(r.verdict, r.reason) for r in results] == [(Verdict.SUPPORTED, ""), (Verdict.NOT_SUPPORTED, "P6 says deposed")]
    assert call.asked[0][2]["properties"]["verdicts"]["items"]["required"] == ["i", "v"]  # no reason demanded for a supported one


def test_the_checker_still_reads_the_older_long_verdicts_and_silence_is_never_approval():
    sources = {"P6": SourcePassage("P6", "Marcos was deposed in 1986.")}
    sentences = [AnswerSentence("Marcos was deposed.", ("P6",)), AnswerSentence("Other.", ("P6",))]
    results = GeminiAnswerChecker(Settings(), Call({"verdicts": [{"index": 0, "verdict": "supported", "reason": ""}]})).check(sentences, sources)
    assert results[0].verdict is Verdict.SUPPORTED and results[1].verdict is Verdict.NOT_SUPPORTED
