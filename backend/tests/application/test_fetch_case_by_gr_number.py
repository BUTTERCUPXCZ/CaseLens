"""A G.R. number can have a Decision and later Resolutions under it: a number (typed, or read from a file) opens the Decision."""
import pytest

from caselens.application.use_cases.fetch_case_by_gr_number import FetchCaseByGrNumber
from caselens.domain.errors import SourceUnavailableError
from caselens.domain.value_objects import DocType, GrNumber
from tests.fakes import InMemoryCaseRepository
from tests.helpers import parse_digest_case

DECISION, RESOLUTION, LATER = "https://lawphil.net/sep1989.html", "https://lawphil.net/oct1989.html", "https://lawphil.net/1990.html"


class Locator:
    def __init__(self, urls):
        self.urls = urls

    def locate(self, gr_no, claimed_year):
        return list(self.urls)


class Ingest:
    """Opens (and stores) a page: each URL is a page of one kind; `down` pages fail like Lawphil not answering."""

    def __init__(self, cases, kinds, down=()):
        self.cases, self.kinds, self.down, self.opened = cases, kinds, set(down), []

    def execute(self, url):
        existing = self.cases.get_by_source_url(url)
        if existing:
            return existing
        self.opened.append(url)
        if url in self.down:
            raise SourceUnavailableError("down")
        case = parse_digest_case("gr_180046_2009.html")
        case.source_url, case.doc_type = url, self.kinds[url]
        return self.cases.add(case)


def fetch(urls, kinds, down=(), cases=None):
    cases = cases or InMemoryCaseRepository()
    ingest = Ingest(cases, kinds, down)
    return FetchCaseByGrNumber(Locator(urls), ingest, cases), ingest


def test_the_decision_is_opened_and_one_page_is_enough_when_it_comes_first():
    use_case, ingest = fetch([DECISION, RESOLUTION], {DECISION: DocType.DECISION, RESOLUTION: DocType.RESOLUTION})
    assert use_case.execute(GrNumber("180046"), None).source_url == DECISION and ingest.opened == [DECISION]


def test_when_a_resolution_comes_first_the_decision_after_it_is_found():
    use_case, ingest = fetch([RESOLUTION, DECISION], {DECISION: DocType.DECISION, RESOLUTION: DocType.RESOLUTION})
    assert use_case.execute(GrNumber("180046"), None).source_url == DECISION and ingest.opened == [RESOLUTION, DECISION]


def test_with_no_decision_among_the_first_pages_the_first_page_is_the_answer():
    kinds = {RESOLUTION: DocType.RESOLUTION, LATER: DocType.RESOLUTION, DECISION: DocType.DECISION}
    use_case, ingest = fetch([RESOLUTION, LATER, "https://lawphil.net/x.html", DECISION], {**kinds, "https://lawphil.net/x.html": DocType.UNKNOWN})
    assert use_case.execute(GrNumber("180046"), None).source_url == RESOLUTION and len(ingest.opened) == 3  # never more than 3 pages


def test_a_later_page_failing_keeps_the_page_already_found_but_a_first_page_failing_says_so():
    use_case, _ = fetch([RESOLUTION, DECISION], {RESOLUTION: DocType.RESOLUTION, DECISION: DocType.DECISION}, down={DECISION})
    assert use_case.execute(GrNumber("180046"), None).source_url == RESOLUTION
    use_case, _ = fetch([DECISION], {DECISION: DocType.DECISION}, down={DECISION})
    with pytest.raises(SourceUnavailableError):
        use_case.execute(GrNumber("180046"), None)


def test_a_library_holding_only_the_resolution_gets_the_decision_and_a_stored_decision_needs_no_lookup():
    cases = InMemoryCaseRepository()
    use_case, ingest = fetch([RESOLUTION, DECISION], {RESOLUTION: DocType.RESOLUTION, DECISION: DocType.DECISION}, cases=cases)
    ingest.execute(RESOLUTION)  # stored by an earlier upload
    ingest.opened.clear()
    assert use_case.execute(GrNumber("180046"), None).source_url == DECISION and ingest.opened == [DECISION]
    ingest.opened.clear()
    assert use_case.execute(GrNumber("180046"), None).source_url == DECISION and ingest.opened == []  # now stored: no request
