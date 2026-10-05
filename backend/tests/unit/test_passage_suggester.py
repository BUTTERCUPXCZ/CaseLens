"""The rules that find the Court's own statement of the Issue when it did not label one, measured on the 31 real decisions
whose Issue was marked by hand (`tests/fixtures/digest/gold.json`, written before any rule or model ran).

The standard is not "find as many as possible" but "never suggest a wrong passage": a missed issue costs the student
a click, a wrong one costs their trust.
"""
import json
from pathlib import Path

import pytest

from caselens.domain.digest import ParagraphRange
from caselens.domain.services.heading_sections import HeadingSections
from caselens.domain.services.passage_suggester import IssueFinder
from caselens.domain.services.ruling_locator import RulingLocator

from ..helpers import digest_paragraphs

GOLD = {k: v for k, v in json.loads((Path(__file__).resolve().parent.parent / "fixtures" / "digest" / "gold.json").read_text()).items() if not k.startswith("_")}
WITH_HEADING = {"gr_125548_1998.html", "gr_148263_2009.html", "gr_165678_2009.html", "gr_173081_2010.html", "gr_175483_2015.html"}


def suggest(name: str):
    paragraphs = digest_paragraphs(name)
    ruling = RulingLocator().locate(paragraphs)
    return IssueFinder().find(paragraphs, HeadingSections.body_start(paragraphs), ruling.first if ruling else None)


def gold_paragraphs(name: str) -> set[int]:
    return {i for first, last in (GOLD[name]["issues"] or []) for i in range(first, last + 1)}


@pytest.mark.parametrize("name", GOLD)
def test_a_suggestion_is_never_wrong(name):
    found = suggest(name)
    if GOLD[name]["issues"] is None:
        assert found is None, f"the Court states no issue here, but {found} was suggested"
    elif found is not None:
        suggested = set(found.range.indexes())
        assert suggested & gold_paragraphs(name), f"{found} is not where the Court states the issue ({GOLD[name]['issues']})"


def test_enough_real_issues_are_found_to_be_useful():
    found = [name for name in GOLD if GOLD[name]["issues"] is not None and suggest(name) is not None]
    assert len(found) >= 14  # 15 of 27 when written; the rest are for the AI step


def test_decisions_that_state_no_issue_get_none():
    assert [name for name in GOLD if GOLD[name]["issues"] is None and suggest(name) is not None] == []


def test_the_range_is_the_statement_and_its_list_and_stops_before_the_discussion():
    found = suggest("gr_148263_2009.html")  # "David raises the following issues before this Court:" + 3 numbered issues
    assert found.range == ParagraphRange(34, 37) and "raises the following issues" in found.reason


def test_a_line_that_only_labels_the_section_is_never_the_suggestion():
    paragraphs = ["Manila", "Assignment of Error", "Petitioner raises the following error:", "I", "THE LOWER COURT ERRED IN HOLDING THAT THE SALE WAS VALID", "The Court finds the petition without merit."]
    found = IssueFinder().find(paragraphs, 1, 5)
    assert found.range == ParagraphRange(2, 4)


def test_a_passing_mention_of_the_issue_is_not_a_statement_of_it():
    paragraphs = ["x", "The issue before us is not novel. It is settled that an employee guilty of misconduct gets no separation pay."]
    assert IssueFinder().find(paragraphs, 1, 2) is None
    paragraphs = ["x", "On the issue of the improbability of the sale, the Court finds this a flimsy and shallow defense."]
    assert IssueFinder().find(paragraphs, 1, 2) is None


def test_a_lower_courts_grounds_are_not_the_issue():
    paragraphs = ["x", "On 12 February 2001, the respondents filed a motion to dismiss on the following grounds: that the court had no jurisdiction."]
    assert IssueFinder().find(paragraphs, 1, 2) is None


def test_nothing_before_the_body_or_after_the_ruling_is_searched():
    paragraphs = ["The issue is whether the caption counts.", "Facts of the case, told at length.", "The issue is whether it was said after the ruling.", "SO ORDERED."]
    assert IssueFinder().find(paragraphs, 1, 2) is None
    assert IssueFinder().find(paragraphs, None, 2) is None


def test_a_long_labelled_issue_is_cut_back_to_the_statement_and_its_questions():
    # Marcos v. Manglapus: after "The Issue" the statement, a lead-in and numbered questions, then ordinary discussion.
    paragraphs = (
        ["Manila", "The Issue", "Th issue is basically one of power: whether or not the President may bar the return.", "According to the petitioners, the case depends on the following issues:"]
        + ["1. Does the President have the power to bar the return?", "a. Is this a political question?", "2. Assuming that the President has the power,", "(1) Have the requirements of due process been complied with?"]
        + ["The case for petitioners is founded on the assertion that the right to return is a liberty.", "Section 1. No person shall be deprived of liberty.", "x x x x x x x x x"]
        + ["More discussion of the Constitution and of the powers of the President."] * 60
    )
    labelled = ParagraphRange(2, len(paragraphs) - 1)
    assert IssueFinder().cap(paragraphs, labelled) == ParagraphRange(2, 7)


def test_a_short_labelled_issue_is_left_alone():
    paragraphs = ["x", "The Issue", "The main issue is whether the petitioner may have mandamus.", "Next heading"]
    assert IssueFinder().cap(paragraphs, ParagraphRange(2, 2)) == ParagraphRange(2, 2)
