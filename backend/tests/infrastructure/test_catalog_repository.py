"""The catalog in PostgreSQL, loaded from REAL parsed Lawphil months (1987-03, 2009-04, 2015-07).
Expected results are computed with plain Python over the parsed rows, not with SQL."""
import time
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import text

from caselens.application.use_cases.search_catalog import SearchCatalog
from caselens.domain.entities import CatalogEntry, IndexPage
from caselens.domain.services.catalog_query import CatalogQueryParser
from caselens.domain.value_objects import GrNumber
from caselens.infrastructure.db.catalog_repository import SqlCatalogRepository
from caselens.infrastructure.db.repositories import SqlCaseRepository
from caselens.infrastructure.lawphil.catalog_parser import LawphilCatalogParser
from caselens.infrastructure.lawphil.html_decoding import decode_html
from tests.helpers import parse_official_case

pytestmark = pytest.mark.db

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "catalog"
MONTHS = [("mar1987.html", 1987, 3, "mar"), ("apr2009.html", 2009, 4, "apr"), ("jul2015.html", 2015, 7, "jul")]


def month_page(year: int, month: int, code: str) -> IndexPage:
    return IndexPage(year, month, f"https://lawphil.net/judjuris/juri{year}/{code}{year}/{code}{year}.html")


@pytest.fixture
def loaded(db_session):
    """The three real months stored in the catalog; returns (repository, all parsed entries)."""
    repo = SqlCatalogRepository(db_session)
    everything: list[CatalogEntry] = []
    for name, year, month, code in MONTHS:
        page = month_page(year, month, code)
        parsed = LawphilCatalogParser().parse(decode_html((FIXTURES / name).read_bytes(), "text/html"), page.url)
        repo.replace_month(page, parsed.entries)
        everything.extend(parsed.entries)
    return repo, everything


def search(repo, text_, year=None, limit=500, offset=0):
    return SearchCatalog(repo).execute(text_, year, limit, offset)


def test_a_search_by_words_finds_the_real_review_center_case(loaded):
    repo, entries = loaded
    page = search(repo, "review center ermita")
    expected = [e for e in entries if all(w in e.title.lower() for w in ("review", "center", "ermita"))]
    assert expected and page.total == len(expected)  # the data really contains it
    assert any("180046" in hit.entry.numbers for hit in page.hits)
    assert page.understood_as == "name"


@pytest.mark.parametrize("typed", ["180046", "G.R. No. 180046", "gr 180046"])
def test_a_search_by_number_however_it_is_typed(loaded, typed):
    repo, _ = loaded
    page = search(repo, typed)
    assert [h.entry.numbers for h in page.hits] == [("180046",)]
    assert page.understood_as == "number"
    assert page.hits[0].entry.decision_date == date(2009, 4, 2)


def test_a_number_prefix_matches_every_row_that_has_a_number_starting_with_it(loaded):
    repo, entries = loaded
    expected = {e.source_url + "|".join(e.numbers) for e in entries if any(n.startswith("180") for n in e.numbers)}
    page = search(repo, "G.R. No. 180")
    assert page.total == len(expected) > 1
    assert {h.entry.source_url + "|".join(h.entry.numbers) for h in page.hits} == expected


def test_every_number_of_a_joint_decision_finds_it(loaded):
    repo, _ = loaded
    for number in ("211972", "212045"):  # "G.R. Nos. 211972 & 212045", July 22, 2015
        hits = search(repo, number).hits
        assert [h.entry.numbers for h in hits] == [("211972", "212045")]
        assert hits[0].entry.also_decided_with == ("212045",) if number == "211972" else True
    assert [h.entry.numbers for h in search(repo, "148272").hits] == [("148263", "148271", "148272")]  # a range


@pytest.mark.parametrize("typed", ["L-28156", "l28156", "G.R. No. L-28156"])
def test_old_style_numbers(loaded, typed):
    repo, _ = loaded
    hits = search(repo, typed).hits
    assert [h.entry.numbers for h in hits] == [("L-28156",)] and hits[0].entry.decision_date == date(1987, 3, 31)


def test_results_are_newest_first_and_paged(loaded):
    repo, entries = loaded
    page = search(repo, "people philippines", limit=500)
    years = [h.entry.decision_date.year for h in page.hits if h.entry.decision_date]
    assert years == sorted(years, reverse=True) and len(set(years)) >= 2
    first = search(repo, "people philippines", limit=5, offset=0)
    second = search(repo, "people philippines", limit=5, offset=5)
    assert first.total == second.total == page.total
    assert [h.entry.source_url for h in first.hits + second.hits] == [h.entry.source_url for h in page.hits[:10]]


def test_the_year_narrows_the_search(loaded):
    repo, entries = loaded
    expected = [e for e in entries if "people" in e.title.lower() and e.decision_date and e.decision_date.year == 2009]
    page = search(repo, "people", year=2009)
    assert page.total == len(expected) > 0 and all(h.entry.decision_date.year == 2009 for h in page.hits)
    assert search(repo, "people", year=1999).total == 0


def test_a_case_already_in_the_library_is_marked_with_its_id(loaded, db_session):
    repo, _ = loaded
    saved = SqlCaseRepository(db_session).add(parse_official_case())  # GR 180046 from the real page
    hit = search(repo, "180046").hits[0]
    assert hit.case_id == saved.id
    other = search(repo, "G.R. No. 180").hits
    assert {h.entry.numbers[0]: h.case_id for h in other}["180046"] == saved.id
    assert all(h.case_id is None for h in other if "180046" not in h.entry.numbers)


def test_a_typed_percent_or_underscore_is_not_a_wildcard(db_session):
    """(synthetic rows) a student typing '100%' must find only a title that really contains it."""
    repo = SqlCatalogRepository(db_session)
    page = month_page(2000, 1, "jan")
    rows = [("100% Pure Corp vs. Juan", ("111111",)), ("Alpha vs. Beta", ("222222",)), ("A_B Trading vs. C", ("333333",))]
    repo.replace_month(
        page,
        [CatalogEntry(GrNumber(n[0]), n, t, date(2000, 1, 5), f"https://lawphil.net/judjuris/juri2000/jan2000/gr_{n[0]}_2000.html", page.url) for t, n in rows],
    )
    assert [h.entry.numbers for h in search(repo, "100%").hits] == [("111111",)]
    assert search(repo, "%").understood_as == "nothing"  # a bare wildcard is not a search at all
    assert [h.entry.numbers for h in search(repo, "a_b").hits] == [("333333",)]  # not "any character": Alpha is not matched


def test_reading_a_month_again_replaces_it_instead_of_duplicating(db_session):
    repo = SqlCatalogRepository(db_session)
    page = month_page(2009, 4, "apr")
    parsed = LawphilCatalogParser().parse(decode_html((FIXTURES / "apr2009.html").read_bytes(), "text/html"), page.url)
    repo.replace_month(page, parsed.entries)
    first_total = search(repo, "people").total

    repo.replace_month(page, parsed.entries)  # the daily re-read of the current month
    assert search(repo, "people").total == first_total

    repo.replace_month(page, parsed.entries[:3])  # the list shrank: old rows must go
    assert search(repo, "people").total <= 3
    assert repo.read_months() == {(2009, 4)}


def test_find_by_number_for_looking_a_case_up(loaded):
    repo, _ = loaded
    (entry,) = repo.find_by_number(GrNumber("180046"))
    assert entry.source_url.endswith("/apr2009/gr_180046_2009.html")
    assert repo.find_by_number(GrNumber("999999")) == []
    joint = repo.find_by_number(GrNumber("212045"))
    assert joint[0].source_url.endswith("gr_211972_2015.html")  # opens the page the row links to


def test_status_tells_empty_partial_and_ready_apart(db_session):
    repo = SqlCatalogRepository(db_session)
    assert (repo.status(False).state, repo.status(False).entries) == ("empty", 0)

    april, may = month_page(2009, 4, "apr"), month_page(2009, 5, "may")
    repo.register_months([april, may])  # Lawphil lists two months; none read yet
    status = repo.status(False)
    assert (status.state, status.months_known, status.months_read, status.percent) == ("empty", 2, 0, 0)

    parsed = LawphilCatalogParser().parse(decode_html((FIXTURES / "apr2009.html").read_bytes(), "text/html"), april.url)
    repo.replace_month(april, parsed.entries)
    status = repo.status(False)
    assert (status.state, status.months_read, status.months_known, status.entries, status.percent) == ("partial", 1, 2, 157, 50)
    assert repo.status(True).state == "building"

    repo.replace_month(may, [])  # an empty month still counts as read
    assert (repo.status(False).state, repo.status(False).percent) == ("ready", 100)


def test_registering_a_month_twice_does_not_reset_one_already_read(db_session):
    repo = SqlCatalogRepository(db_session)
    page = month_page(2009, 4, "apr")
    repo.register_months([page])
    repo.replace_month(page, [])
    repo.register_months([page])
    assert repo.read_months() == {(2009, 4)}


def test_a_broken_month_is_recorded_but_not_counted_as_read(db_session):
    repo = SqlCatalogRepository(db_session)
    repo.replace_month(month_page(2010, 5, "may"), [], broken=True)
    assert repo.read_months() == set()  # it will be tried again


def test_search_over_60_000_rows_is_fast_and_uses_the_indexes(db_session):
    """(synthetic) the real catalog is about this size. The rows go into TEMPORARY tables that
    shadow the real ones for this test only: they are private to the session, so no other run
    sees them and autovacuum never has to clean up after them (it made this test take
    over a minute when it wrote into the real tables and rolled back)."""
    for table in ("catalog_entries", "catalog_numbers"):
        db_session.execute(text(f"CREATE TEMP TABLE {table} (LIKE public.{table} INCLUDING ALL) ON COMMIT DROP"))
    db_session.execute(text("SET LOCAL search_path = pg_temp, public"))
    db_session.execute(text("""
        INSERT INTO catalog_entries (id, source_url, link_number, label_key, title, decision_date, year, month, index_url)
        SELECT n, 'https://lawphil.net/x/gr_' || n || '_' || y || '.html', n::text, n::text,
               (ARRAY['Juan','Maria','People of the Philippines','Court of Appeals','Santos','Reyes','Bank of the Philippine Islands'])[1 + n % 7]
                 || ' ' || (ARRAY['Cruz','Garcia','Lopez','Ramos','Torres'])[1 + n % 5] || ' vs. ' || (ARRAY['Aquino','Mendoza','Bautista'])[1 + n % 3] || ' ' || n,
               make_date(y, 1 + n % 12, 1 + n % 28), y, 1 + n % 12, 'https://lawphil.net/x/index.html'
        FROM (SELECT g AS n, 1987 + (g % 40) AS y FROM generate_series(100000, 160000) g) s
    """))
    db_session.execute(text("INSERT INTO catalog_numbers (id, entry_id, number) SELECT id, id, link_number FROM catalog_entries"))
    db_session.execute(text("ANALYZE catalog_entries"))
    db_session.execute(text("ANALYZE catalog_numbers"))
    assert db_session.scalar(text("SELECT count(*) FROM catalog_entries")) >= 60_000

    repo = SqlCatalogRepository(db_session)
    for typed in ("garcia aquino", "G.R. No. 1234", "santos lopez 1500"):
        started = time.perf_counter()
        page = search(repo, typed, limit=20)
        elapsed_ms = (time.perf_counter() - started) * 1000
        assert page.total > 0 and elapsed_ms < 100, (typed, elapsed_ms)

    # The indexes are really usable (forced, because a planner may prefer a scan on a tiny table).
    # Temp copies get generated index names, so check the plan's shape instead of a name.
    db_session.execute(text("SET LOCAL enable_seqscan = off"))
    number_plan = "\n".join(r[0] for r in db_session.execute(text("EXPLAIN SELECT 1 FROM catalog_numbers WHERE number LIKE '1234%'")))
    title_plan = "\n".join(r[0] for r in db_session.execute(text("EXPLAIN SELECT 1 FROM catalog_entries WHERE title ILIKE '%garcia%'")))
    assert "Index" in number_plan and "Seq Scan" not in number_plan, number_plan
    assert "Bitmap Index Scan" in title_plan and "Seq Scan" not in title_plan, title_plan  # the trigram GIN index


def test_a_month_that_lawphil_lists_but_does_not_serve_does_not_leave_the_catalog_unfinished(db_session):
    repo = SqlCatalogRepository(db_session)
    april, may = month_page(2009, 4, "apr"), month_page(2009, 5, "may")
    repo.register_months([april, may])
    parsed = LawphilCatalogParser().parse(decode_html((FIXTURES / "apr2009.html").read_bytes(), "text/html"), april.url)
    repo.replace_month(april, parsed.entries)
    assert repo.status(False).state == "partial"

    repo.mark_absent(may)  # the page answered 404

    status = repo.status(False)
    assert (status.state, status.percent) == ("ready", 100)
    assert repo.read_months() == {(2009, 4)}  # not "read": the next build checks it again


def test_a_row_with_exactly_the_typed_number_comes_before_rows_that_only_start_with_it(db_session):
    """(synthetic) '14744' must show G.R. 14744 first, then 147443 and 147440, not the other way round."""
    repo = SqlCatalogRepository(db_session)
    page = month_page(2000, 1, "jan")
    rows = [("147443", date(2008, 2, 11)), ("14744", date(1988, 5, 3)), ("147440", date(2004, 1, 1))]  # newest first would put 14744 last
    repo.replace_month(page, [
        CatalogEntry(GrNumber(n), (n,), f"Case {n} vs. Other", d, f"https://lawphil.net/judjuris/juri2000/jan2000/gr_{n}_2000.html", page.url)
        for n, d in rows
    ])
    assert [h.entry.numbers[0] for h in search(repo, "14744").hits] == ["14744", "147443", "147440"]


def test_an_old_number_typed_without_its_l_prefix_is_still_found(loaded):
    """Real March 1987 row: `G.R. No. L-28156`. A student types 28156."""
    repo, _ = loaded
    assert [h.entry.numbers for h in search(repo, "28156").hits] == [("L-28156",)]
    assert [h.entry.numbers for h in search(repo, "G.R. No. 2815").hits][:1] == [("L-28156",)]  # prefix, too
