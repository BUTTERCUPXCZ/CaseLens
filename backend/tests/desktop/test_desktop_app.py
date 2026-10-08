"""The desktop app's own parts: its local server, settings, backup and restore, and the shipped catalog."""
from datetime import date
from pathlib import Path

import sqlite3

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, insert, select

from caselens.desktop import api as desktop_api
from caselens.infrastructure.db.catalog_seed import export_catalog, import_catalog
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
        self.groq_api_key = self.deepseek_api_key = self.openrouter_api_key = None
        self.ai_provider = "gemini"
        self.groq_model, self.deepseek_model, self.gemini_writer_model = "openai/gpt-oss-120b", "deepseek-flash", "gemini-3.5-flash"
        self.openrouter_model = "deepseek/deepseek-v4.1-flash"
        self.ai_only_chosen = False


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
    monkeypatch.setattr(desktop_api, "save_ai_key", lambda _folder, key, provider="gemini": setattr(settings, f"{provider}_api_key", key))
    monkeypatch.setattr(desktop_api, "save_provider", lambda _folder, provider: setattr(settings, "ai_provider", provider))
    monkeypatch.setattr(desktop_api, "check_gemini_key", lambda key: key != "not-a-real-key")  # no calls to Google in tests
    monkeypatch.setattr(desktop_api, "check_key", lambda provider, key: key != "not-a-real-key")
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


def test_with_a_launch_code_only_the_apps_own_window_gets_in(tmp_path, screens, monkeypatch):
    """Another program on this computer (no cookie) is refused; the app's window opens with the code once and then uses a
    private cookie, so the code does not stay in the address."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    settings = _Settings(data_dir)
    monkeypatch.setattr(desktop_api, "get_settings", lambda: settings)
    app = create_desktop_app(screens, launch_token="s3cret-code")

    stranger = TestClient(app, base_url=LOCAL)
    assert stranger.get("/").status_code == 403
    assert stranger.get("/api/desktop/settings").status_code == 403
    assert stranger.get("/?launch=wrong").status_code == 403
    assert stranger.get("/api/health").status_code != 403  # the app's start check needs no code

    window = TestClient(app, base_url=LOCAL)
    opened = window.get("/?launch=s3cret-code")
    assert opened.status_code == 200 and 'location.replace("/")' in opened.text  # moves on to the library by itself
    assert "httponly" in opened.headers["set-cookie"].lower() and "samesite=strict" in opened.headers["set-cookie"].lower()
    window.cookies.set("caselens_launch", "s3cret-code")
    assert window.get("/").text == "<div id=root></div>"
    assert window.get("/api/desktop/settings").status_code == 200


def test_the_key_file_is_private_from_the_start(tmp_path, monkeypatch):
    import builtins
    import stat

    from caselens.desktop import ai_key

    real_import = builtins.__import__

    def no_keyring(name, *args, **kwargs):
        if name == "keyring":
            raise ImportError("no password store")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_keyring)
    ai_key.save_ai_key(str(tmp_path), "secret-key")
    path = tmp_path / "ai-key.txt"
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert ai_key.read_ai_key(str(tmp_path)) == "secret-key"
    ai_key.save_ai_key(str(tmp_path), None)
    assert not path.exists()


def test_a_new_version_copies_the_library_first_and_keeps_the_last_three(tmp_path):
    from caselens.desktop.server import backup_before_update

    library = tmp_path / "caselens.db"
    with sqlite3.connect(library) as connection:
        connection.execute("CREATE TABLE notes (text TEXT)")
        connection.execute("INSERT INTO notes VALUES ('my digest edits')")

    assert backup_before_update(tmp_path, "1.1.0") is None  # first start of the app: nothing to keep yet
    assert backup_before_update(tmp_path, "1.1.0") is None  # same version again: no copy
    copy = backup_before_update(tmp_path, "1.2.0")
    assert copy == tmp_path / "backups" / "before-1.2.0.db"
    with sqlite3.connect(copy) as connection:
        assert connection.execute("SELECT text FROM notes").fetchall() == [("my digest edits",)]

    for version in ["1.3.0", "1.4.0", "1.5.0"]:
        backup_before_update(tmp_path, version)
    assert sorted(p.name for p in (tmp_path / "backups").iterdir()) == ["before-1.3.0.db", "before-1.4.0.db", "before-1.5.0.db"]
    assert (tmp_path / "version.txt").read_text() == "1.5.0"


def test_a_key_google_refuses_is_not_saved_and_says_why(desktop):
    refused = desktop.put("/api/desktop/ai-key", json={"key": "not-a-real-key"})
    assert refused.status_code == 400 and "not a valid Gemini API key" in refused.json()["detail"]
    assert desktop.get("/api/desktop/settings").json()["ai_key_set"] is False


def test_settings_say_when_the_saved_key_is_refused_or_out_of_credit(desktop):
    from caselens.infrastructure.ai import calls, gemini_answerer

    calls.forget_key_problem()
    gemini_answerer._note_key_problem("invalid")
    assert desktop.get("/api/desktop/settings").json()["ai_key_invalid"] is True
    gemini_answerer._note_key_problem("credit")
    body = desktop.get("/api/desktop/settings").json()
    assert body["ai_out_of_credit"] is True and body["ai_key_invalid"] is False
    desktop.put("/api/desktop/ai-key", json={"key": "a-new-working-key"})  # a new key: the warning goes
    assert desktop.get("/api/desktop/settings").json()["ai_out_of_credit"] is False


def test_each_provider_has_its_own_key_and_the_chosen_one_writes_first(desktop):
    from caselens.infrastructure.ai import calls

    calls.forget_key_problem()
    assert desktop.put("/api/desktop/ai-key", json={"provider": "groq", "key": "gsk_working"}).status_code == 200
    body = desktop.put("/api/desktop/ai-provider", json={"provider": "groq"}).json()
    assert body["ai_provider"] == "groq" and body["ai_key_set"] is True
    groq = next(p for p in body["providers"] if p["id"] == "groq")
    assert groq == {"id": "groq", "name": "Groq", "model": "openai/gpt-oss-120b", "key_set": True, "problem": None}
    assert next(p for p in body["providers"] if p["id"] == "deepseek")["key_set"] is False

    refused = desktop.put("/api/desktop/ai-key", json={"provider": "deepseek", "key": "not-a-real-key"})
    assert refused.status_code == 400 and "DeepSeek says" in refused.json()["detail"]
    assert desktop.put("/api/desktop/ai-provider", json={"provider": "openai"}).status_code == 422  # only the three


def test_the_openrouter_model_and_only_the_chosen_ai_are_set_in_settings(desktop, monkeypatch, tmp_path):
    from caselens.desktop import ai_key

    settings = desktop_api.get_settings()
    monkeypatch.setattr(desktop_api, "save_openrouter_model", lambda _folder, model: setattr(settings, "openrouter_model", model))
    monkeypatch.setattr(desktop_api, "save_only_chosen", lambda _folder, only: setattr(settings, "ai_only_chosen", only))
    body = desktop.get("/api/desktop/settings").json()
    assert [m["id"] for m in body["openrouter_models"]] == ["deepseek/deepseek-v4.1-flash", "nvidia/nemotron-3-ultra-550b-a55b:free"]

    body = desktop.put("/api/desktop/openrouter-model", json={"model": "nvidia/nemotron-3-ultra-550b-a55b:free"}).json()
    assert body["openrouter_model"] == "nvidia/nemotron-3-ultra-550b-a55b:free"
    assert desktop.put("/api/desktop/openrouter-model", json={"model": "anything/else"}).status_code == 400  # only the offered models
    assert desktop.put("/api/desktop/ai-only-chosen", json={"only": True}).json()["ai_only_chosen"] is True

    # the choices are kept in the app's folder and read back (the real save functions)
    folder = tmp_path / "kept"
    folder.mkdir()
    assert ai_key.read_only_chosen(str(folder)) is True  # on unless turned off
    ai_key.save_only_chosen(str(folder), False)
    ai_key.save_openrouter_model(str(folder), "nvidia/nemotron-3-ultra-550b-a55b:free")
    assert ai_key.read_only_chosen(str(folder)) is False
    assert ai_key.read_openrouter_model(str(folder)) == "nvidia/nemotron-3-ultra-550b-a55b:free"
