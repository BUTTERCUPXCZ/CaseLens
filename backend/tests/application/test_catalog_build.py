from datetime import date

import pytest

from caselens.application.use_cases.build_catalog import BuildCatalog
from caselens.application.use_cases.keep_catalog_fresh import KeepCatalogFresh
from tests.fakes import (
    FakeCatalogParser,
    FakeIndexFetcher,
    FakeJobQueue,
    FakeYearDiscovery,
    InMemoryCatalogRepository,
    page_url,
)

TODAY = date(2009, 5, 10)  # "now" for these tests: the current month is May 2009, the previous April 2009


class Setup:
    def __init__(self, months_by_year=None, today=TODAY):
        self.discovery = FakeYearDiscovery(months_by_year or {1986: [1, 2], 1987: [1, 2, 3], 2009: [3, 4, 5]})
        self.fetcher = FakeIndexFetcher()
        self.parser = FakeCatalogParser()
        self.catalog = InMemoryCatalogRepository()
        self.use_case = BuildCatalog(self.discovery, self.fetcher, self.parser, self.catalog, today=lambda: today)

    def fetched_months(self) -> list[tuple[int, int]]:
        urls = {page_url(y, m): (y, m) for y in range(1980, 2030) for m in range(1, 13)}
        return [urls[u] for u in self.fetcher.fetched]


def test_a_build_reads_every_listed_month_from_the_first_year_newest_first():
    s = Setup()
    report = s.use_case.build(first_year=1987)

    assert s.fetched_months() == [(2009, 5), (2009, 4), (2009, 3), (1987, 3), (1987, 2), (1987, 1)]
    assert (report.read, report.skipped, report.entries) == (6, 0, 6)
    assert 1986 not in s.discovery.months_asked  # before the first year: never even listed


def test_progress_has_an_honest_total_before_the_first_page_is_read():
    s = Setup()
    seen = []
    original = s.fetcher.fetch

    def spy(url):
        seen.append((len(s.catalog.months), len(s.catalog.read_months())))
        return original(url)

    s.fetcher.fetch = spy
    s.use_case.build(first_year=1987)

    assert seen[0] == (6, 0)  # all 6 months known, none read: "0 of 6" can be shown from the start
    assert seen[-1] == (6, 5)


def test_a_second_build_resumes_and_only_reads_what_is_new_or_recent():
    s = Setup()
    s.use_case.build(first_year=1987)
    s.fetcher.fetched.clear()

    report = s.use_case.build(first_year=1987)

    assert s.fetched_months() == [(2009, 5), (2009, 4)]  # the current and previous month are always re-read
    assert (report.read, report.skipped) == (2, 4)


def test_a_build_stopped_halfway_continues_where_it_stopped():
    s = Setup()
    s.catalog.months[(2009, 5)] = "read"  # earlier run got this far (newest first)
    s.catalog.months[(2009, 4)] = "read"
    s.catalog.months[(2009, 3)] = "read"
    s.use_case.build(first_year=1987)
    assert s.fetched_months() == [(2009, 5), (2009, 4), (1987, 3), (1987, 2), (1987, 1)]  # 2009-03 not repeated


def test_a_listed_month_that_cannot_be_downloaded_is_missing_not_an_error():
    s = Setup()
    s.fetcher.pages[page_url(1987, 2)] = None  # Lawphil lists it, the page answers 404
    report = s.use_case.build(first_year=1987)
    assert report.missing == [page_url(1987, 2)] and report.failed == []
    assert (1987, 2) not in s.catalog.read_months()  # not recorded as read, so it is tried next time
    assert s.catalog.months[(1987, 2)] == "absent"  # but counted as handled, so progress can reach 100%
    assert report.read == 5
    assert s.catalog.status(building=False).state == "ready"


def test_one_month_that_fails_does_not_stop_the_rest():
    s = Setup()
    s.fetcher.down.add(page_url(2009, 4))
    report = s.use_case.build(first_year=1987)
    assert [url for url, _ in report.failed] == [page_url(2009, 4)] and "down" in report.failed[0][1]
    assert report.read == 5 and (2009, 3) in s.catalog.read_months() and (1987, 1) in s.catalog.read_months()


def test_a_year_page_that_will_not_load_does_not_stop_the_other_years():
    s = Setup()
    s.discovery.failing_years.add(1987)
    report = s.use_case.build(first_year=1987)
    assert report.read == 3 and {y for y, _ in s.catalog.read_months()} == {2009}


def test_a_page_with_links_but_nothing_readable_is_reported_as_broken():
    s = Setup()
    s.parser.broken_pages.add(page_url(2009, 3))
    report = s.use_case.build(first_year=1987)
    assert report.broken == [page_url(2009, 3)]
    assert s.catalog.months[(2009, 3)] == "broken" and (2009, 3) not in s.catalog.read_months()


def test_refresh_reads_only_the_current_and_previous_month():
    s = Setup()
    report = s.use_case.refresh()
    assert s.fetched_months() == [(2009, 5), (2009, 4)] and report.read == 2
    assert s.discovery.months_asked == [2009]  # one year page, not forty


def test_refresh_in_january_also_reads_december_of_the_year_before():
    s = Setup(months_by_year={2009: [11, 12], 2010: [1]}, today=date(2010, 1, 15))
    s.use_case.refresh()
    assert s.fetched_months() == [(2010, 1), (2009, 12)]
    assert sorted(s.discovery.months_asked) == [2009, 2010]


# -- KeepCatalogFresh -----------------------------------------------------------------


def test_an_empty_catalog_starts_the_one_time_build_on_the_first_search():
    catalog, jobs = InMemoryCatalogRepository(), FakeJobQueue()
    assert KeepCatalogFresh(catalog, jobs, first_year=1987).execute() == "building"
    assert jobs.catalog_builds == [1987] and jobs.catalog_refreshes == 0


def test_a_second_search_while_the_build_runs_does_not_start_another():
    catalog, jobs = InMemoryCatalogRepository(), FakeJobQueue()
    jobs.catalog_build_running = True
    KeepCatalogFresh(catalog, jobs, first_year=1987).execute()
    assert jobs.catalog_builds == []


def test_a_filled_catalog_asks_for_the_daily_refresh_but_only_once():
    s = Setup()
    s.use_case.build(first_year=1987)
    jobs = FakeJobQueue()
    keep = KeepCatalogFresh(s.catalog, jobs, first_year=1987)

    assert keep.execute() == "ready"
    keep.execute()
    keep.execute()

    assert jobs.catalog_refreshes == 1 and jobs.catalog_builds == []  # the day's lock held back the others
