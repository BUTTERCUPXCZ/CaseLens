"""The website's own start-up work: the shipped catalog copied into PostgreSQL, and staying awake while work is waiting."""
import threading
from datetime import date

import pytest
from sqlalchemy import delete, func, insert, select

from caselens.infrastructure.db.catalog_seed import export_catalog, import_catalog, seed_catalog_in_background
from caselens.infrastructure.db.orm_models import CatalogEntryModel, CatalogMonthModel, CatalogNumberModel
from caselens.infrastructure.db.session import make_engine
from caselens.infrastructure.db.sqlite_schema import upgrade_sqlite
from caselens.infrastructure.keep_awake import keep_awake_while_busy


def _seed(tmp_path):
    url = f"sqlite:///{(tmp_path / 'source.db').as_posix()}"
    upgrade_sqlite(url)
    source = make_engine(url)
    with source.begin() as connection:
        entry_id = connection.execute(insert(CatalogEntryModel.__table__).returning(CatalogEntryModel.id), {
            "source_url": "https://lawphil.net/judjuris/juri2009/apr2009/gr_180046_2009.html", "link_number": "180046",
            "label_key": "180046", "title": "Review Center Associations v. Ermita", "decision_date": date(2009, 4, 2),
            "year": 2009, "month": 4, "index_url": "https://lawphil.net/judjuris/juri2009/apr2009/apr2009.html",
        }).scalar_one()
        connection.execute(insert(CatalogNumberModel.__table__), {"entry_id": entry_id, "number": "180046"})
    source.dispose()
    seed = tmp_path / "catalog.sqlite"
    export_catalog(url, seed)
    return seed


@pytest.fixture
def empty_catalog(test_engine):
    def clear():
        with test_engine.begin() as connection:
            for table in (CatalogNumberModel.__table__, CatalogEntryModel.__table__, CatalogMonthModel.__table__):
                connection.execute(delete(table))
    clear()
    yield test_engine
    clear()


def test_the_shipped_catalog_fills_the_websites_database_and_later_rows_still_get_new_ids(tmp_path, empty_catalog, postgres_only):
    seed = _seed(tmp_path)
    assert import_catalog(empty_catalog, seed) == 1
    assert import_catalog(empty_catalog, seed) == 0  # already filled: never doubled
    with empty_catalog.begin() as connection:  # the daily refresh adds rows without an id: the counter was moved past the copied ones
        connection.execute(insert(CatalogEntryModel.__table__), {
            "source_url": "https://lawphil.net/judjuris/juri2026/oct2026/gr_1_2026.html", "link_number": "1", "label_key": "1",
            "title": "A v. B", "decision_date": date(2026, 10, 1), "year": 2026, "month": 10, "index_url": "https://lawphil.net/x.html",
        })
        assert connection.execute(select(func.count()).select_from(CatalogEntryModel.__table__)).scalar_one() == 2


def test_the_copy_runs_in_the_background_and_holds_the_build_lock(tmp_path, empty_catalog):
    seed_catalog_in_background(empty_catalog, _seed(tmp_path)).join(timeout=30)
    with empty_catalog.connect() as connection:
        assert connection.execute(select(func.count()).select_from(CatalogEntryModel.__table__)).scalar_one() == 1


def test_a_missing_seed_file_leaves_the_catalog_to_be_built(tmp_path, empty_catalog):
    seed_catalog_in_background(empty_catalog, tmp_path / "missing.sqlite").join(timeout=30)
    with empty_catalog.connect() as connection:
        assert connection.execute(select(func.count()).select_from(CatalogEntryModel.__table__)).scalar_one() == 0


def _run_keep_awake(work: list[bool]) -> list[str]:
    """Three rounds with the given answers to "is work waiting?"; returns the addresses called."""
    pinged, stop, rounds = [], threading.Event(), iter(work)

    def has_work():
        answer = next(rounds, None)
        if answer is None:
            stop.set()
            return False
        return answer

    keep_awake_while_busy("https://caselens.example.com/", has_work=has_work, ping=pinged.append, every=0.001, stop=stop).join(timeout=5)
    return pinged


def test_the_site_calls_itself_only_while_work_is_waiting():
    assert _run_keep_awake([True, False, True]) == ["https://caselens.example.com/health"] * 2


def test_a_failed_call_never_stops_the_keep_awake():
    pinged, stop, calls = [], threading.Event(), iter([True, True])

    def ping(url):
        pinged.append(url)
        if len(pinged) == 1:
            raise OSError("host asleep")

    def has_work():
        answer = next(calls, None)
        if answer is None:
            stop.set()
        return bool(answer)

    keep_awake_while_busy("https://x.example.com", has_work=has_work, ping=ping, every=0.001, stop=stop).join(timeout=5)
    assert len(pinged) == 2
