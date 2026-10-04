import pytest

from caselens.infrastructure.db.repositories import SqlMonthIndexRepository

pytestmark = pytest.mark.db

URL = "https://lawphil.net/judjuris/juri2009/apr2009/apr2009.html"


def test_unknown_url_is_none(db_session):
    assert SqlMonthIndexRepository(db_session).get(URL) is None


def test_save_then_get_round_trips_and_replaces(db_session):
    repo = SqlMonthIndexRepository(db_session)
    repo.save(URL, ["a.html", "b.html"])
    assert repo.get(URL) == ["a.html", "b.html"]

    repo.save(URL, ["c.html"])
    assert repo.get(URL) == ["c.html"]


def test_empty_list_is_a_valid_cached_value(db_session):
    """An empty list means 'fetched, nothing there' and must differ from 'never fetched'."""
    repo = SqlMonthIndexRepository(db_session)
    repo.save(URL, [])
    assert repo.get(URL) == []
