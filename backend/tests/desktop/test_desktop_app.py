"""The desktop app's own parts: its local server, settings, backup and restore, and the shipped catalog."""
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, insert, select

from caselens.desktop import api as desktop_api
from caselens.desktop.catalog_seed import export_catalog, import_catalog
from caselens.desktop.server import apply_pending_restore, create_desktop_app
from caselens.infrastructure.db.orm_models import CatalogEntryModel, CatalogNumberModel
from caselens.infrastructure.db.session import make_engine
from caselens.infrastructure.db.sqlite_schema import upgrade_sqlite

LOCAL = "http://127.0.0.1:8765"


def _library(path: Path):
    url = f"sqlite:///{path.as_posix()}"
    upgrade_sqlite(url)
    return make_engine(url)


class _Settings:
    def __init__(self, data_dir: Path, key: str | None = None) -> None:
        self.caselens_data_dir, self.gemini_api_key = str(data_dir), key


@pytest.fixture
def screens(tmp_path) -> Path:
    folder = tmp_path / "dist"
    (folder / "assets").mkdir(parents=True)
    (folder / "index.html").write_text("<div id=root></div>")
    (folder / "assets" / "app.js").write_text("console.log(1)")
    return folder


@pytest.fixture
def desktop(tmp_path, screens, monkeypatch) -> TestClient:
    """The desktop server with its library in a temporary folder."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    engine = _library(data_dir / "caselens.db")
    settings = _Settings(data_dir)
    getter = lambda: settings  # noqa: E731
    getter.cache_clear = lambda: None
    monkeypatch.setattr(desktop_api, "get_settings", getter)
    monkeypatch.setattr(desktop_api, "engine", engine)
    monkeypatch.setattr(desktop_api, "save_ai_key", lambda _folder, key: setattr(settings, "gemini_api_key", key))
    yield TestClient(create_desktop_app(screens), base_url=LOCAL, headers={"Origin": LOCAL})
    engine.dispose()


def test_the_screens_and_any_page_address_load_the_app(desktop):
    assert desktop.get("/").text == "<div id=root></div>"
    assert desktop.get("/library?tab=cases").text == "<div id=root></div>"  # the screen's own router shows the page
    assert desktop.get("/assets/app.js").status_code == 200
    assert desktop.get("/assets/missing.js").status_code == 404  # a missing file is not dressed up as the app


def test_other_websites_cannot_reach_the_library(desktop):
    assert desktop.post("/api/desktop/restore", headers={"Origin": "https://evil.example"}).status_code == 403
    assert desktop.get("/api/desktop/backup", headers={"Sec-Fetch-Site": "cross-site"}).status_code == 403
    assert desktop.get("/", headers={"Host": "evil.example"}).status_code == 403  # DNS rebinding
    assert desktop.post("/api/desktop/restore", headers={"Origin": "http://127.0.0.1:3000"}).status_code == 403  # another local site
    assert desktop.post("/api/desktop/restore", headers={"Origin": ""}).status_code == 403  # no origin on a change
    assert desktop.get("/api/desktop/backup", headers={"Sec-Fetch-Site": "same-site"}).status_code == 403
    assert desktop.get("/api/desktop/backup", headers={"Sec-Fetch-Site": "same-origin"}).status_code == 200


def test_the_ai_key_is_saved_but_never_shown(desktop):
    assert desktop.get("/api/desktop/settings").json()["ai_key_set"] is False
    body = desktop.put("/api/desktop/ai-key", json={"key": "  secret-key  "}).json()
    assert body["ai_key_set"] is True and "secret-key" not in str(body)
    assert desktop.put("/api/desktop/ai-key", json={"key": ""}).json()["ai_key_set"] is False


def test_a_backup_can_be_restored_and_other_files_are_refused(desktop, tmp_path):
    backup = desktop.get("/api/desktop/backup")
    assert backup.status_code == 200 and backup.headers["content-disposition"].startswith("attachment; filename=\"caselens-backup-")

    assert desktop.post("/api/desktop/restore", files={"file": ("x.db", b"not a library")}).status_code == 400
    assert desktop.get("/api/desktop/settings").json()["restore_pending"] is False

    body = desktop.post("/api/desktop/restore", files={"file": ("b.db", backup.content)}).json()
    assert body["restore_pending"] is True
    assert (tmp_path / "data" / desktop_api.RESTORE_FILE).read_bytes() == backup.content


def test_a_pending_restore_replaces_the_library_and_keeps_the_old_one(tmp_path):
    (tmp_path / "caselens.db").write_text("old")
    (tmp_path / "caselens.db-wal").write_text("old changes")
    (tmp_path / desktop_api.RESTORE_FILE).write_text("backup")

    assert apply_pending_restore(tmp_path) is True
    assert (tmp_path / "caselens.db").read_text() == "backup"
    assert (tmp_path / "caselens-before-restore.db").read_text() == "old"
    assert (tmp_path / "caselens-before-restore.db-wal").read_text() == "old changes"
    assert not (tmp_path / desktop_api.RESTORE_FILE).exists()
    assert apply_pending_restore(tmp_path) is False


def test_the_shipped_catalog_fills_an_empty_library_once(tmp_path):
    source = _library(tmp_path / "source.db")
    with source.begin() as connection:
        entry_id = connection.execute(insert(CatalogEntryModel.__table__).returning(CatalogEntryModel.id), {
            "source_url": "https://lawphil.net/judjuris/juri2009/may2009/gr_180046_2009.html", "link_number": "180046",
            "label_key": "180046", "title": "Review Center Associations v. Ermita", "decision_date": date(2009, 4, 2),
            "year": 2009, "month": 4, "index_url": "https://lawphil.net/judjuris/juri2009/apr2009/apr2009.html",
        }).scalar_one()
        connection.execute(insert(CatalogNumberModel.__table__), {"entry_id": entry_id, "number": "180046"})
    source.dispose()
    seed = tmp_path / "catalog.sqlite"
    assert export_catalog(f"sqlite:///{(tmp_path / 'source.db').as_posix()}", seed) == 1

    library = _library(tmp_path / "caselens.db")
    assert import_catalog(library, seed) == 1
    assert import_catalog(library, seed) == 0  # already filled: never doubled
    assert import_catalog(library, tmp_path / "missing.sqlite") == 0
    with library.connect() as connection:
        assert connection.execute(select(func.count()).select_from(CatalogNumberModel.__table__)).scalar_one() == 1
    library.dispose()
