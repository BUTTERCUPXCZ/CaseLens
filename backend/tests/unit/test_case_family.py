"""One case, one row: which stored page is the main case when several pages describe the same case."""
from caselens.domain.services.case_family import CaseFamily, FamilyMember
from caselens.domain.value_objects import DocType


def member(id, numbers, doc_type=DocType.DECISION, main=None):
    return FamilyMember(id, frozenset(numbers), doc_type, main)


def place(numbers, doc_type, stored):
    return CaseFamily().place(numbers, doc_type, stored)


def test_a_page_nobody_else_prints_is_a_main_case():
    decision = place(["180046"], DocType.DECISION, [member(1, ["173931"])])
    assert decision.main_case_id is None and decision.repoint == ()


def test_the_same_decision_found_again_under_another_url_joins_the_main_case():
    assert place(["88211"], DocType.DECISION, [member(1, ["88211"])]).main_case_id == 1


def test_a_resolution_joins_the_decision_it_follows_and_is_not_listed_on_its_own():
    assert place(["79690", "79707"], DocType.RESOLUTION, [member(3, ["79690", "79691", "79707"])]).main_case_id == 3


def test_a_decision_stored_after_its_resolution_becomes_the_main_case_and_the_family_follows_it():
    decision = place(["79690"], DocType.DECISION, [member(1, ["79690"], DocType.RESOLUTION)])
    assert decision.main_case_id is None and decision.repoint == (1,)


def test_a_joint_decision_page_that_shares_one_number_with_a_stored_page_is_the_same_case():
    assert place(["148271", "148272"], DocType.DECISION, [member(1, ["148263", "148271"])]).main_case_id == 1


def test_a_new_page_joins_the_main_row_not_a_related_one():
    stored = [member(1, ["88211"]), member(2, ["88211"], DocType.RESOLUTION, main=1)]
    assert place(["88211"], DocType.RESOLUTION, stored).main_case_id == 1


def test_a_decision_outranks_an_unknown_page_but_an_unknown_page_does_not_outrank_a_decision():
    assert place(["1"], DocType.DECISION, [member(1, ["1"], DocType.UNKNOWN)]).repoint == (1,)
    assert place(["1"], DocType.UNKNOWN, [member(1, ["1"], DocType.DECISION)]).main_case_id == 1


def test_a_decision_that_outranks_the_main_row_takes_the_whole_family():
    stored = [member(1, ["5"], DocType.RESOLUTION), member(2, ["5"], DocType.RESOLUTION, main=1)]
    decision = place(["5"], DocType.DECISION, stored)
    assert decision.main_case_id is None and set(decision.repoint) == {1, 2}
