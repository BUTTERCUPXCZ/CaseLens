"""The safety rules around the digest writer, with a scripted writer and checker (no AI): nothing reaches the digest unless its cited
paragraphs exist, its numbers and names are in the decision, and a second model says "supported"; a rewrite faces the same checks."""
import pytest

from caselens.application.ports.ai import DigestRequest
from caselens.application.use_cases.write_case_digest import WriteCaseDigest
from caselens.domain.digest import AnswerSentence, SourcePassage
from caselens.domain.digest_v2 import LEVEL_SECTIONS, DigestBlock, DigestDraft, Level, Section
from tests.fakes import ScriptedDigestWriter, VerdictChecker

SOURCES = (
    SourcePassage("C1", "FERDINAND E. MARCOS, petitioners, vs. HONORABLE RAUL MANGLAPUS, respondents. G.R. No. 88211 September 15, 1989 EN BANC"),
    SourcePassage("P6", "In February 1986, Ferdinand E. Marcos was deposed from the presidency via the non-violent people power revolution."),
    SourcePassage("P9", "The President has decided to bar the Marcoses from returning, citing dire consequences to the nation's stability."),
    SourcePassage("O2.1", "(Cruz, J., dissenting) It is my belief that the petitioner, as a citizen, is entitled to return to his country."),
)
REQUEST = DigestRequest(SOURCES, "Marcos v. Manglapus, G.R. No. 88211", "Constitutional Law", ())


def draft(*sentences, section=Section.FACTS, as_list=False):
    return DigestDraft({section: (DigestBlock(tuple(AnswerSentence(t, tuple(c)) for t, c in sentences), None, as_list),)})


def run(writer, checker=None, **kwargs):
    return WriteCaseDigest(writer, checker or VerdictChecker(), **kwargs).execute(REQUEST)


def texts(result, section=Section.FACTS):
    return [s.text for block in result.draft.sections.get(section, ()) for s in block.sentences]


def test_a_backed_sentence_passes():
    result = run(ScriptedDigestWriter(draft(("In February 1986, Marcos was deposed.", ["P6"]))))
    assert texts(result) == ["In February 1986, Marcos was deposed."] and result.dropped == []


def test_a_sentence_citing_a_paragraph_that_does_not_exist_is_dropped():
    result = run(ScriptedDigestWriter(draft(("Marcos was deposed.", ["P99"])), repairs={}))
    assert texts(result) == [] and "does not exist" in result.dropped[0].reason


def test_a_number_that_is_nowhere_in_the_decision_is_dropped_but_one_from_another_paragraph_is_kept():
    result = run(ScriptedDigestWriter(draft(("Marcos was deposed in 1986.", ["P9"]), ("Marcos was deposed in 1999.", ["P6"]))), repair=False)
    assert texts(result) == ["Marcos was deposed in 1986."]  # 1986 is in P6: a digest may use a number from elsewhere in the decision
    assert "1999" in result.dropped[0].reason


def test_a_name_the_decision_never_mentions_is_dropped_but_the_caption_and_opinion_authors_count():
    writer = ScriptedDigestWriter(draft(("Justice Cruz agreed with Manglapus.", ["O2.1", "C1"]), ("Justice Roxas agreed.", ["P6"])))
    result = run(writer, repair=False)
    assert texts(result) == ["Justice Cruz agreed with Manglapus."]
    assert "Roxas" in result.dropped[0].reason


def test_the_second_model_must_say_supported():
    sentence = "The President was ousted by the military."
    result = run(ScriptedDigestWriter(draft((sentence, ["P6"]), ("Marcos was deposed.", ["P6"]))), VerdictChecker({sentence}), repair=False)
    assert texts(result) == ["Marcos was deposed."] and "checker" in result.dropped[0].reason


def test_an_honest_not_stated_sentence_needs_no_citation_but_a_claim_without_one_is_dropped():
    result = run(ScriptedDigestWriter(draft(("The decision does not say who the justices were.", []), ("The President was wrong.", []))), repair=False)
    assert texts(result) == ["The decision does not say who the justices were."]
    assert result.dropped[0].reason == "no source cited"


def test_a_not_stated_sentence_with_a_number_is_not_waved_through():
    result = run(ScriptedDigestWriter(draft(("The decision does not say that 12 justices voted.", []))), repair=False)
    assert texts(result) == []


def test_a_rewrite_that_passes_replaces_the_sentence_in_its_place():
    first, bad, last = ("Marcos was deposed.", ["P6"]), ("The President feared a coup in 1999.", ["P9"]), ("The President decided to bar the return.", ["P9"])
    writer = ScriptedDigestWriter(draft(first, bad, last), repairs={0: AnswerSentence("The President cited dire consequences to stability.", ("P9",))})
    result = run(writer)
    assert texts(result) == ["Marcos was deposed.", "The President cited dire consequences to stability.", "The President decided to bar the return."]
    assert result.repaired == 1 and result.dropped == []
    assert writer.repair_calls[0][0][1] == "The President feared a coup in 1999."  # the writer was told what failed, and why


def test_a_rewrite_that_fails_the_same_checks_is_dropped_too():
    writer = ScriptedDigestWriter(draft(("The President feared a coup in 1999.", ["P9"])), repairs={0: AnswerSentence("Still wrong in 1999.", ("P9",))})
    result = run(writer)
    assert texts(result) == [] and len(result.dropped) == 1 and result.repaired == 0


def test_with_repair_off_nothing_is_rewritten():
    writer = ScriptedDigestWriter(draft(("Marcos was deposed in 1999.", ["P6"])), repairs={0: AnswerSentence("Marcos was deposed.", ("P6",))})
    assert texts(run(writer, repair=False)) == [] and writer.repair_calls == []


def test_a_section_with_nothing_left_is_absent_not_filled_in():
    result = run(ScriptedDigestWriter(draft(("Marcos was deposed in 1999.", ["P6"]), section=Section.DOCTRINE)), repair=False)
    assert Section.DOCTRINE not in result.draft.sections


@pytest.mark.parametrize("level", list(Level))
def test_every_level_prints_the_header_sections_the_client_asked_for(level):
    sections = LEVEL_SECTIONS[level]
    assert Section.DOCTRINE in sections and Section.FACTS in sections  # all three levels start with Doctrine and Facts
    assert (Section.RATIO in sections) is (level is Level.FULL) and (Section.ISSUE in sections) is (level is not Level.SHORT)


class SlowChecker(VerdictChecker):
    """Takes a while per group, like the real model; can fail on the group that holds a given sentence."""

    def __init__(self, unsupported=(), seconds=0.3, fail_on=None):
        super().__init__(unsupported)
        self.seconds, self.fail_on = seconds, fail_on

    def check(self, sentences, sources):
        import time

        time.sleep(self.seconds)
        if self.fail_on and any(s.text == self.fail_on for s in sentences):
            from caselens.domain.errors import AiUnavailableError

            raise AiUnavailableError("the checker did not answer")
        return super().check(sentences, sources)


def _many(n):
    words = ["first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth"]
    return [(f"In February 1986, Marcos was deposed, as the {words[k % 10]} line of part {words[k // 10]} says.", ["P6"]) for k in range(n)]


def test_the_check_groups_are_judged_at_the_same_time_and_the_result_keeps_the_writers_order():
    import time

    lines = _many(70)  # three groups of up to 25
    checker = SlowChecker(unsupported={lines[30][0]})
    started = time.monotonic()
    result = run(ScriptedDigestWriter(draft(*lines)), checker, repair=False)
    elapsed = time.monotonic() - started

    assert len(checker.seen) == 3
    assert elapsed < 0.6  # about one group's wait (0.3 s), not three (0.9 s)
    assert texts(result) == [text for text, _ in lines if text != lines[30][0]]  # same order as written, the unsupported one gone
    assert [d.text for d in result.dropped] == [lines[30][0]]


def test_a_check_group_that_fails_still_fails_the_digest():
    from caselens.domain.errors import AiUnavailableError

    lines = _many(60)
    with pytest.raises(AiUnavailableError):
        run(ScriptedDigestWriter(draft(*lines)), SlowChecker(seconds=0.01, fail_on=lines[40][0]), repair=False)
