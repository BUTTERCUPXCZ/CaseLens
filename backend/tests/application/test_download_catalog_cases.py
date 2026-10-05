from dataclasses import replace
from datetime import date

from caselens.application.use_cases.download_catalog_cases import DownloadCatalogCases
from caselens.domain.entities import CatalogEntry, IndexPage
from caselens.domain.errors import CaseParseError, SourceUnavailableError
from caselens.domain.value_objects import GrNumber
from tests.fakes import InMemoryCatalogRepository


def entry(number: str, year: int = 2009) -> CatalogEntry:
    url = f"https://lawphil.net/judjuris/juri{year}/gr_{number}_{year}.html"
    return CatalogEntry(GrNumber(number), (number,), f"Case {number}", date(year, 4, 2), url, "https://lawphil.net/index")


class Ingest:
    """Stands in for IngestCase: remembers what it saved, and can fail on chosen pages."""

    def __init__(self, catalog, fail=None):
        self.catalog, self.fail, self.saved = catalog, fail or {}, []

    def execute(self, url):
        if url in self.fail:
            raise self.fail[url]
        self.saved.append(url)
        self.catalog.saved_urls.add(url)


def catalog_with(*entries: CatalogEntry) -> InMemoryCatalogRepository:
    catalog = InMemoryCatalogRepository()
    for e in entries:
        catalog.entries.setdefault((e.decision_date.year, 4), []).append(e)
    return catalog


def run(catalog, ingest, **kw):
    rolled = []
    report = DownloadCatalogCases(catalog, ingest, lambda: rolled.append(1)).execute(kw.pop("first", 1987), kw.pop("last", 2100), **kw)
    return report, rolled


def test_it_saves_every_listed_page_once_and_a_joint_decision_is_one_page():
    joint_a = entry("148263")
    joint_b = replace(entry("148271"), source_url=joint_a.source_url)  # one page listed under two numbers
    catalog = catalog_with(entry("111"), joint_a, joint_b, entry("222"))
    ingest = Ingest(catalog)

    report, _ = run(catalog, ingest)

    assert report.saved == 3 and len(ingest.saved) == 3 and report.failed == []


def test_running_it_again_carries_on_with_what_is_missing():
    catalog = catalog_with(entry("111"), entry("222"), entry("333"))
    first = Ingest(catalog)
    run(catalog, first, limit=2)
    second = Ingest(catalog)

    report, _ = run(catalog, second)

    assert len(first.saved) == 2 and len(second.saved) == 1 and report.saved == 1


def test_a_page_that_cannot_be_read_is_reported_and_the_rest_carry_on():
    bad = entry("222")
    catalog = catalog_with(entry("111"), bad, entry("333"))
    ingest = Ingest(catalog, fail={bad.source_url: CaseParseError("no title")})

    report, rolled = run(catalog, ingest)

    assert report.saved == 2 and [u for u, _ in report.failed] == [bad.source_url] and rolled == [1]


def test_it_stops_when_lawphil_keeps_not_answering_instead_of_hammering_it():
    entries = [entry(str(1000 + i)) for i in range(40)]
    catalog = catalog_with(*entries)
    ingest = Ingest(catalog, fail={e.source_url: SourceUnavailableError("down") for e in entries})

    report, _ = run(catalog, ingest)

    assert report.stopped and "Run it again later" in report.stopped and len(report.failed) == 25


def test_only_the_years_asked_for_are_saved():
    catalog = catalog_with(entry("111", 2008), entry("222", 2010))
    ingest = Ingest(catalog)

    run(catalog, ingest, first=2010, last=2010)

    assert [u.rsplit("_", 2)[1] for u in ingest.saved] == ["222"]
