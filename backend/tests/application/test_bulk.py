"""Bulk upload: each number or file is ONE main case; cited cases are never added; repeats are shown once; nothing is lost on a failure."""
import pytest

from caselens.application.use_cases.bulk import MAX_FILES_PER_REQUEST, AddBulkFiles, GetBulkBatch, ResolveBulkItem, RetryBulkBatch, StartBulkBatch
from caselens.application.use_cases.case_digest_v2 import RequestCaseDigestV2
from caselens.domain.bulk import ItemKind, ItemStatus
from caselens.domain.errors import CaseNotFoundError, DomainError, SourceUnavailableError, UnsupportedDocumentError
from caselens.domain.services.gr_list_parser import GrListParser
from caselens.domain.services.main_case_identifier import MainCaseIdentifier
from tests.fakes import (
    FakeJobQueue,
    FakeUnitOfWork,
    InMemoryBulkRepository,
    InMemoryCaseDigestRepository,
    InMemoryCaseRepository,
    InMemorySubjectRepository,
)
from tests.helpers import parse_digest_case


class Lawphil:
    """What FetchCaseByGrNumber does: the case for a number, or "not found", or Lawphil down."""

    def __init__(self, cases):
        self.cases, self.known, self.down, self.asked = cases, {}, set(), []

    def add(self, number, name, **changes):
        case = parse_digest_case(name)
        case.source_url = f"https://lawphil.net/{number}"
        for key, value in changes.items():
            setattr(case, key, value)
        self.known[number] = self.cases.add(case)
        return self.known[number]

    def find_stored(self, number):
        return None

    def execute(self, number, year):
        self.asked.append((number.value, year))
        if number.value in self.down:
            raise SourceUnavailableError("down")
        if number.value not in self.known:
            raise CaseNotFoundError(f"G.R. No. {number} was not found.")
        return self.known[number.value]


class Reader:
    def __init__(self, texts):
        self.texts = texts

    def read(self, filename, data):
        if filename not in self.texts:
            raise UnsupportedDocumentError("We can read PDF and Word files.")
        return self.texts[filename]


class World:
    def __init__(self):
        self.cases, self.bulk, self.jobs, self.uow = InMemoryCaseRepository(), InMemoryBulkRepository(), FakeJobQueue(), FakeUnitOfWork()
        self.subjects = InMemorySubjectRepository()
        self.cases.subject_names = {s.id: s.name for s in self.subjects.subjects}
        self.lawphil = Lawphil(self.cases)
        self.digests = InMemoryCaseDigestRepository()
        self.start = StartBulkBatch(GrListParser(), self.subjects, self.bulk, self.jobs, self.uow)
        self.reader = Reader({})
        self.files = AddBulkFiles(self.reader, MainCaseIdentifier(), self.bulk, self.jobs, self.uow)
        self.resolve = ResolveBulkItem(self.bulk, self.lawphil, self.cases, RequestCaseDigestV2(self.cases, self.digests, self.jobs, self.uow), self.uow)
        self.get = GetBulkBatch(self.bulk)

    def run_all(self, batch_id):
        for item in list(self.bulk.items_by_id.values()):
            if item.batch_id == batch_id:
                self.resolve.execute(item.id)

    def statuses(self, batch_id):
        return [(i.label, i.status.value) for i in sorted((i for i in self.bulk.items_by_id.values() if i.batch_id == batch_id), key=lambda i: i.position)]


@pytest.fixture
def world():
    return World()


CAPTION = "EN BANC\nG.R. No. 180046 April 2, 2009\nREVIEW CENTER ASSOCIATION v. ERMITA\nD E C I S I O N\nCARPIO, J.:\nAs held in Ople v. Torres, G.R. No. 127685, July 23, 1998, and in G.R. No. 111111."


def test_pasted_numbers_become_items_and_what_is_not_a_number_is_kept_as_skipped(world):
    batch = world.start.execute("180046\nbanana\nG.R. No. 173931")
    assert [(i.label, i.status) for i in batch.items] == [("180046", ItemStatus.QUEUED), ("banana", ItemStatus.UNREADABLE), ("G.R. No. 173931", ItemStatus.QUEUED)]
    assert world.jobs.bulk_items == [batch.items[0].id, batch.items[2].id]  # only the readable ones are queued
    assert batch.items[1].message == "This is not a G.R. number, so it was skipped."


def test_the_tags_and_scope_for_the_whole_upload_are_kept_and_an_unknown_tag_is_refused(world):
    with pytest.raises(DomainError, match="does not exist"):
        world.start.execute("1", [4, 99])
    batch = world.start.execute("", [4, 9, 4], "  Presidential   powers ")  # an empty batch is fine: files follow
    assert batch.subject_ids == (4, 9) and batch.topic_scope == "Presidential powers"


def test_a_file_is_one_main_case_and_the_cases_it_cites_are_never_added(world):
    world.reader.texts = {"ermita.pdf": CAPTION}
    batch = world.start.execute("")
    items = world.files.execute(batch.id, [("ermita.pdf", b"x")])
    assert [(i.kind, i.gr_no, i.year) for i in items] == [(ItemKind.FILE, "180046", 2009)]
    assert len(world.bulk.items_by_id) == 1  # not 3: Ople v. Torres and G.R. No. 111111 are only cited


def test_a_file_with_no_readable_caption_number_is_kept_as_an_item_that_says_so(world):
    world.reader.texts = {"notes.pdf": "My notes\nSee G.R. No. 12345."}
    batch = world.start.execute("")
    items = world.files.execute(batch.id, [("notes.pdf", b"x"), ("photo.png", b"x")])
    assert [(i.label, i.status) for i in items] == [("notes.pdf", ItemStatus.UNREADABLE), ("photo.png", ItemStatus.UNREADABLE)]
    assert "could not find a case in this file" in items[0].message and "PDF and Word" in items[1].message
    assert world.jobs.bulk_items == []


def test_files_are_added_a_few_at_a_time_to_a_batch_that_exists(world):
    batch = world.start.execute("")
    with pytest.raises(DomainError, match="at most"):
        world.files.execute(batch.id, [("a.pdf", b"x")] * (MAX_FILES_PER_REQUEST + 1))
    with pytest.raises(CaseNotFoundError):
        world.files.execute(999, [("a.pdf", b"x")])


def test_found_cases_are_filed_and_their_digest_is_asked_for_once(world):
    case = world.lawphil.add("180046", "gr_180046_2009.html")
    batch = world.start.execute("180046", [3], "Board exams")
    world.run_all(batch.id)
    item = world.bulk.items_by_id[batch.items[0].id]
    assert (item.status, item.case_id) == (ItemStatus.FOUND, case.id)
    assert world.cases.tags[case.id] == {3: "batch"}
    digest = world.digests.get(case.id, "board exams")
    assert digest is not None and digest.scope == "Board exams" and world.jobs.case_digests == [digest.id]  # the digest for the upload's scope


def test_a_number_that_lawphil_does_not_have_is_not_found_with_its_reason(world):
    batch = world.start.execute("999999")
    world.run_all(batch.id)
    item = world.bulk.items_by_id[batch.items[0].id]
    assert item.status is ItemStatus.NOT_FOUND and "not on Lawphil's list" in item.message and "999999 (1969)" in item.message
    assert world.jobs.case_digests == []


def test_a_number_with_a_year_that_is_not_found_says_which_year_was_tried(world):
    batch = world.start.execute("999999 (1969)")
    world.run_all(batch.id)
    assert world.bulk.items_by_id[batch.items[0].id].message == "G.R. No. 999999 was not found on Lawphil near 1969."


def test_the_same_case_given_twice_or_under_two_of_its_numbers_is_shown_once(world):
    world.lawphil.add("148263", "gr_148263_2009.html", numbers=("148263", "148271", "148272"))
    world.lawphil.known["148271"] = world.lawphil.known["148263"]  # one decision, found under another of its numbers
    batch = world.start.execute("148263\n148271\n148263")
    world.run_all(batch.id)
    assert world.statuses(batch.id) == [("148263", "found"), ("148271", "duplicate"), ("148263", "duplicate")]
    assert "148263" in world.bulk.items_by_id[batch.items[1].id].message
    assert world.jobs.case_digests == [world.lawphil.known["148263"].id]  # one digest, asked for once


def test_a_resolution_of_a_case_resolves_to_its_main_case(world):
    main = world.lawphil.add("79690", "gr_180046_2009.html")
    related = world.lawphil.add("79691", "gr_173931_2009.html", main_case_id=main.id)
    batch = world.start.execute("79691")
    world.run_all(batch.id)
    assert world.bulk.items_by_id[batch.items[0].id].case_id == main.id and related.id != main.id


def test_an_uploads_tags_are_added_and_tags_the_case_already_has_stay(world):
    case = world.lawphil.add("180046", "gr_180046_2009.html")
    world.cases.add_subjects(case.id, [2], "student")
    world.run_all(world.start.execute("180046", [3, 2]).id)
    assert world.cases.tags[case.id] == {2: "student", 3: "batch"}


def test_lawphil_down_leaves_the_item_failed_and_retry_queues_it_again(world):
    world.lawphil.add("180046", "gr_180046_2009.html")
    world.lawphil.down = {"180046"}
    batch = world.start.execute("180046")
    world.run_all(batch.id)
    item = world.bulk.items_by_id[batch.items[0].id]
    assert item.status is ItemStatus.FAILED and "Retry" in item.message

    world.lawphil.down = set()
    world.jobs.bulk_items.clear()
    assert RetryBulkBatch(world.bulk, world.jobs, world.uow).execute(batch.id) == 1
    assert item.status is ItemStatus.QUEUED and world.jobs.bulk_items == [item.id]
    world.resolve.execute(item.id)
    assert item.status is ItemStatus.FOUND


def test_an_item_that_is_already_settled_is_left_alone_when_its_message_arrives_again(world):
    world.lawphil.add("180046", "gr_180046_2009.html")
    batch = world.start.execute("180046")
    world.run_all(batch.id)
    asked = len(world.lawphil.asked)
    world.resolve.execute(batch.items[0].id)
    assert len(world.lawphil.asked) == asked and world.jobs.case_digests == [world.lawphil.known["180046"].id]


def test_progress_counts_every_way_an_item_can_end(world):
    world.lawphil.add("180046", "gr_180046_2009.html")
    batch = world.start.execute("180046\n180046\n999999\nbanana")
    world.run_all(batch.id)
    counts = world.get.execute(batch.id).counts
    assert (counts.total, counts.found, counts.duplicate, counts.not_found, counts.unreadable, counts.queued) == (4, 1, 1, 1, 1, 0)
    assert counts.finished
    with pytest.raises(CaseNotFoundError):
        world.get.execute(999)


def test_items_come_back_in_the_order_given_one_status_at_a_time(world):
    batch = world.start.execute("1111\nbanana\n2222")
    page, total = world.get.items(batch.id, ItemStatus.UNREADABLE, 50, 0)
    assert total == 1 and page[0].label == "banana"
    page, total = world.get.items(batch.id, None, 2, 1)
    assert total == 3 and [i.label for i in page] == ["banana", "2222"]
