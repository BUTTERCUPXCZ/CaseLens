"""A student's text for a section: read back as paragraphs, bullets and subheadings, and shown in the same form to start an edit."""
from caselens.domain.digest import AnswerSentence
from caselens.domain.digest_v2 import DigestBlock, DigestDraft, Section
from caselens.domain.section_edits import parse_section_text, section_text, with_edits

RATIO = (
    DigestBlock((AnswerSentence("Executive power is more than a list.", ("P74",)), AnswerSentence("It has residual powers.", ("P86",))), "1. Executive power"),
    DigestBlock((AnswerSentence("Insurgency.", ("P96",)), AnswerSentence("Coup attempts.", ("P97",))), as_list=True),
)


def test_a_section_is_shown_as_the_student_would_type_it_and_reads_back_the_same_shape():
    text = section_text(RATIO)
    assert text == "# 1. Executive power\nExecutive power is more than a list. It has residual powers.\n\n- Insurgency.\n- Coup attempts."
    back = parse_section_text(text)
    assert [(b.heading, b.as_list, [s.text for s in b.sentences]) for b in back] == [
        ("1. Executive power", False, ["Executive power is more than a list. It has residual powers."]),
        (None, True, ["Insurgency.", "Coup attempts."]),
    ]
    assert all(s.cites == () for b in back for s in b.sentences)  # the student's words cite nothing


def test_an_edit_replaces_only_its_section_and_an_empty_text_removes_it():
    draft = DigestDraft({Section.DOCTRINE: (DigestBlock((AnswerSentence("Rule.", ("P1",)),)),), Section.RATIO: RATIO})
    edited = with_edits(draft, {Section.DOCTRINE: "My doctrine.", Section.RATIO: "   "})
    assert list(edited.sections) == [Section.DOCTRINE] and edited.sections[Section.DOCTRINE][0].sentences[0].text == "My doctrine."
    assert draft.sections[Section.RATIO] == RATIO  # the shared digest itself is not changed
