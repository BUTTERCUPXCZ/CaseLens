"""The case digest Word file: the client's layout, and a level only chooses which sections print."""
import io

import docx
import pytest

from caselens.domain.digest import AnswerSentence
from caselens.domain.digest_v2 import DigestBlock, DigestDraft, Level, Section
from caselens.infrastructure.docx_digest_export import DigestHeader, DocxCaseDigestExporter

HEADER = DigestHeader("Marcos v. Manglapus", "G.R. No. 88211, September 15, 1989 (En Banc)", "Constitutional Law", "Cortes, J.")


def block(*texts, heading=None, as_list=False, cites=("P6", "P7")):
    return DigestBlock(tuple(AnswerSentence(t, cites) for t in texts), heading, as_list)


DRAFT = DigestDraft({
    Section.DOCTRINE: (block("The President has residual powers."),),
    Section.FACTS: (block("Marcos was deposed in 1986.", "Aquino became President."),),
    Section.ARGUMENTS_PETITIONERS: (block("They invoked the right to travel.", "They invoked the right to return.", as_list=True),),
    Section.ISSUE: (block("May the President bar the Marcoses from returning? Yes."),),
    Section.RULING: (block("The petition was dismissed."),),
    Section.RATIO: (block("The Court said so.", heading="1. The right to return"),),
    Section.DISSENTS: (block("He argued rights come first.", heading="Cruz, J., dissenting", cites=("O3.2",)),),
    Section.TOPIC: (block("Executive power is more than a list."),),
    Section.WHY: (block("Remember residual powers.", as_list=True),),
})


def read(level, **kwargs):
    document = docx.Document(io.BytesIO(DocxCaseDigestExporter().export(HEADER, DRAFT, level, **kwargs)))
    return [(p.style.name, p.text) for p in document.paragraphs if p.text.strip()]


def headings(level):
    return [text for style, text in read(level) if style.startswith("Heading 1")]


def test_the_header_is_laid_out_like_the_clients_sample():
    lines = [text for _, text in read(Level.FULL)[:4]]
    assert lines == ["CASE DIGEST", "Marcos v. Manglapus", "G.R. No. 88211, September 15, 1989 (En Banc)", "Topic: Constitutional Law  |  Ponente: Cortes, J."]


def test_the_full_digest_has_every_section_in_the_clients_order():
    assert headings(Level.FULL) == ["Doctrine", "Facts", "Issue", "Ruling", "Ratio Decidendi", "The Dissents (useful for recitation)", "Topic Explained", "Why This Case Matters"]


def test_the_standard_level_stops_after_the_ruling_and_the_short_one_after_the_facts():
    assert headings(Level.STANDARD) == ["Doctrine", "Facts", "Issue", "Ruling"]
    assert headings(Level.SHORT) == ["Doctrine", "Facts"]


def test_the_partys_arguments_are_a_subheading_of_the_facts_and_a_list_prints_as_bullets():
    document = read(Level.SHORT)
    assert ("Heading 2", "Petitioners’ arguments") in document
    assert [text for style, text in document if style == "List Bullet"] == ["They invoked the right to travel.", "They invoked the right to return."]


def test_a_paragraph_block_is_one_paragraph_and_a_block_heading_is_kept():
    document = read(Level.FULL)
    assert ("Normal", "Marcos was deposed in 1986. Aquino became President.") in document
    assert ("Heading 2", "1. The right to return") in document


def test_like_the_clients_sample_there_are_no_paragraph_lines_unless_asked_for():
    assert not any(text.startswith("Based on decision paragraphs") for _, text in read(Level.FULL))
    assert ("Normal", "Based on decision paragraphs 6, 7.") in read(Level.FULL, show_sources=True)


def runs(level=Level.FULL, draft=None):
    document = docx.Document(io.BytesIO(DocxCaseDigestExporter().export(HEADER, draft or DRAFT, level)))
    return [(p.style.name, [(r.text, bool(r.bold)) for r in p.runs]) for p in document.paragraphs if p.text.strip()]


def test_a_key_sentence_is_bold_and_the_rest_of_its_paragraph_is_not():
    key = DigestDraft({Section.RULING: (DigestBlock((AnswerSentence("The petition was DISMISSED.", ("P102",), key=True), AnswerSentence("The Court explained why.", ("P102",)))),)})
    ruling = next(r for style, r in runs(draft=key) if r and r[0][0].startswith("The petition"))
    assert ruling == [("The petition was DISMISSED.", True), (" The Court explained why.", False)]


def test_each_dissent_is_one_item_with_the_justices_name_in_bold_and_the_recitation_points_have_their_lead_in():
    draft = DigestDraft({
        Section.DISSENTS: (DigestBlock((AnswerSentence("Cruz, J.: The government failed to prove a threat.", ("O2.3",)),), as_list=True),),
        Section.WHY: (DigestBlock((AnswerSentence("Residual powers exist.", ("P74",), key=True),), as_list=True),),
    })
    printed = runs(draft=draft)
    assert ("List Bullet", [("Cruz, J.:", True), (" The government failed to prove a threat.", False)]) in printed
    lead = [r for _, r in printed].index([("Remember for recitation:", True)])
    assert printed[lead + 1] == ("List Bullet", [("Residual powers exist.", True)])


def test_it_always_ends_with_the_draft_notice():
    last = read(Level.SHORT)[-1][1]
    assert "draft" in last and "Lawphil" in last


@pytest.mark.parametrize("level", list(Level))
def test_a_section_the_writer_left_empty_is_not_printed(level):
    thin = DigestDraft({Section.FACTS: DRAFT.sections[Section.FACTS]})
    document = docx.Document(io.BytesIO(DocxCaseDigestExporter().export(HEADER, thin, level)))
    assert [p.text for p in document.paragraphs if p.style.name.startswith("Heading 1")] == ["Facts"]
