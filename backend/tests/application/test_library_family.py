"""IngestCase places a new page in its family; the library lists one row per case; the subject belongs to the main case."""
import pytest

from caselens.application.use_cases.ingest_case import IngestCase
from caselens.application.use_cases.list_cases import ListCases
from caselens.application.use_cases.subjects import ListSubjects, SetCaseSubjects
from caselens.domain.errors import CaseNotFoundError, DomainError
from caselens.domain.value_objects import DocType
from tests.fakes import FakeUnitOfWork, InMemoryCaseRepository, InMemorySubjectRepository
from tests.helpers import parse_digest_case


class Pages:
    """A fetcher and a parser that hand back the case prepared for each url."""

    def __init__(self):
        self.by_url = {}

    def add(self, url, name, doc_type=DocType.DECISION, numbers=None):
        case = parse_digest_case(name)
        case.source_url, case.doc_type = url, doc_type
        if numbers:
            case.numbers = tuple(numbers)
        self.by_url[url] = case
        return case

    def fetch(self, url):
        return url

    def parse(self, html, url):
        return self.by_url[url]


@pytest.fixture
def world():
    pages, cases = Pages(), InMemoryCaseRepository()
    cases.subject_names = {s.id: s.name for s in InMemorySubjectRepository().subjects}  # Civil Law 1, Criminal Law 2, Remedial Law 3, Constitutional Law 4, ...
    ingest = IngestCase(pages, pages, cases, FakeUnitOfWork())
    return pages, cases, ingest


def test_two_pages_of_one_case_are_stored_but_listed_once(world):
    pages, cases, ingest = world
    pages.add("u/decision", "gr_180046_2009.html")
    pages.add("u/again", "gr_180046_2009.html")  # the same case found under another link
    first, second = ingest.execute("u/decision"), ingest.execute("u/again")
    assert first.main_case_id is None and second.main_case_id == first.id
    page = ListCases(cases).execute(None, 20, 0)
    assert page.total == 1 and page.items[0].id == first.id  # one row, the main case


def test_a_resolution_stored_before_its_decision_hands_over_the_main_row(world):
    pages, cases, ingest = world
    pages.add("u/resolution", "gr_180046_2009.html", DocType.RESOLUTION)
    pages.add("u/decision", "gr_180046_2009.html", DocType.DECISION)
    resolution = ingest.execute("u/resolution")
    decision = ingest.execute("u/decision")
    assert decision.main_case_id is None and cases.get(resolution.id).main_case_id == decision.id
    assert [i.id for i in ListCases(cases).execute(None, 20, 0).items] == [decision.id]


def test_different_cases_are_each_listed(world):
    pages, cases, ingest = world
    pages.add("u/1", "gr_180046_2009.html")
    pages.add("u/2", "gr_173931_2009.html")
    ingest.execute("u/1"), ingest.execute("u/2")
    assert ListCases(cases).execute(None, 20, 0).total == 2


def test_the_tags_are_set_on_the_main_case_even_when_asked_for_a_related_page(world):
    pages, cases, ingest = world
    pages.add("u/decision", "gr_180046_2009.html")
    pages.add("u/again", "gr_180046_2009.html")
    main, related = ingest.execute("u/decision"), ingest.execute("u/again")
    updated = SetCaseSubjects(cases, InMemorySubjectRepository(), FakeUnitOfWork()).execute(related.id, [4, 9])
    assert updated.id == main.id and [s.name for s in updated.subjects] == ["Constitutional Law", "Political Law"]
    assert cases.tags[main.id] == {4: "student", 9: "student"}


def test_the_library_filters_by_tag_shows_a_case_under_each_of_its_tags_and_counts_them(world):
    pages, cases, ingest = world
    pages.add("u/1", "gr_180046_2009.html")
    pages.add("u/2", "gr_173931_2009.html")
    first, second = ingest.execute("u/1"), ingest.execute("u/2")
    SetCaseSubjects(cases, InMemorySubjectRepository(), FakeUnitOfWork()).execute(first.id, [4, 9])

    assert [i.id for i in ListCases(cases).execute(None, 20, 0, subject_id=4).items] == [first.id]
    assert [i.id for i in ListCases(cases).execute(None, 20, 0, subject_id=9).items] == [first.id]  # under both of its tags
    assert [i.id for i in ListCases(cases).execute(None, 20, 0, no_subject=True).items] == [second.id]
    counts = {c.name: c.count for c in ListSubjects(cases).execute()}
    assert counts["Constitutional Law"] == 1 and counts["Political Law"] == 1 and counts["Civil Law"] == 0 and counts["No subject yet"] == 1


def test_clearing_the_tags_and_refusing_an_unknown_one(world):
    pages, cases, ingest = world
    pages.add("u/1", "gr_180046_2009.html")
    case = ingest.execute("u/1")
    set_tags = SetCaseSubjects(cases, InMemorySubjectRepository(), FakeUnitOfWork())
    set_tags.execute(case.id, [4])
    set_tags.execute(case.id, [])
    assert cases.get(case.id).subjects == ()
    with pytest.raises(DomainError, match="does not exist"):
        set_tags.execute(case.id, [99])
    with pytest.raises(CaseNotFoundError):
        set_tags.execute(12345, [1])


def test_the_results_of_a_batch_show_each_main_case_once_in_the_order_given():
    from caselens.application.use_cases.list_cases import ListBatchCases
    from caselens.domain.bulk import BulkBatch, BulkItem, ItemKind, ItemStatus
    from caselens.domain.entities import CaseSummary  # noqa: F401
    from tests.fakes import InMemoryBulkRepository, InMemoryCaseRepository
    from tests.helpers import parse_digest_case

    cases = InMemoryCaseRepository()
    first = cases.add(parse_digest_case("gr_180046_2009.html"))
    second = cases.add(parse_digest_case("gr_173931_2009.html"))
    bulk = InMemoryBulkRepository()
    batch = bulk.add_batch(BulkBatch(items=[
        BulkItem(0, 0, ItemKind.GR_NUMBER, "173931", "173931", status=ItemStatus.FOUND, case_id=second.id),
        BulkItem(0, 0, ItemKind.GR_NUMBER, "180046", "180046", status=ItemStatus.FOUND, case_id=first.id),
        BulkItem(0, 0, ItemKind.GR_NUMBER, "173931", "173931", status=ItemStatus.FOUND, case_id=second.id),
        BulkItem(0, 0, ItemKind.GR_NUMBER, "999", "999", status=ItemStatus.NOT_FOUND),
    ]))

    page = ListBatchCases(bulk, cases).execute(batch.id, 20, 0)

    assert [c.id for c in page.items] == [second.id, first.id] and page.total == 2
    assert ListBatchCases(bulk, cases).execute(batch.id, 1, 1).items[0].id == first.id


def test_an_uploads_cases_can_be_narrowed_to_the_ready_ones_while_the_rest_are_written():
    """With 50 cases the student studies the finished digests first: the list filters by digest state (for this upload's
    topic scope, not the standard digest), and says how many are in each state."""
    from caselens.application.use_cases.list_cases import ListBatchCases
    from caselens.domain.bulk import BulkBatch, BulkItem, ItemKind, ItemStatus
    from caselens.domain.digest_v2 import CaseDigestV2, DigestState
    from tests.fakes import InMemoryBulkRepository, InMemoryCaseDigestRepository, InMemoryCaseRepository
    from tests.helpers import parse_digest_case

    cases = InMemoryCaseRepository()
    first = cases.add(parse_digest_case("gr_180046_2009.html"))
    second = cases.add(parse_digest_case("gr_173931_2009.html"))
    bulk = InMemoryBulkRepository()
    batch = bulk.add_batch(BulkBatch(topic_scope="Delegation of powers", items=[
        BulkItem(0, 0, ItemKind.GR_NUMBER, "180046", "180046", status=ItemStatus.FOUND, case_id=first.id),
        BulkItem(0, 0, ItemKind.GR_NUMBER, "173931", "173931", status=ItemStatus.FOUND, case_id=second.id),
    ]))
    digests = InMemoryCaseDigestRepository()
    digests.save(CaseDigestV2(first.id, "Delegation of powers", DigestState.READY))
    digests.save(CaseDigestV2(second.id, "", DigestState.READY))  # the standard digest: not this upload's
    digests.save(CaseDigestV2(second.id, "Delegation of powers", DigestState.PENDING))
    listing = ListBatchCases(bulk, cases, digests)

    everything = listing.execute(batch.id, 20, 0)
    assert everything.states == {first.id: "ready", second.id: "pending"}
    assert everything.counts == {"ready": 1, "writing": 1, "failed": 0}
    ready = listing.execute(batch.id, 20, 0, "ready")
    assert [c.id for c in ready.items] == [first.id] and ready.total == 1
    assert [c.id for c in listing.execute(batch.id, 20, 0, "writing").items] == [second.id]
