"""Settings for the desktop app (one user on their own computer): the AI key, and backing up or restoring the library. These routes
exist only in the desktop app: on the website anyone could reach them."""
import os
import sqlite3
import tempfile
from datetime import date
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from caselens.desktop.ai_key import save_ai_key
from caselens.infrastructure.config import get_settings
from caselens.infrastructure.db.session import engine

router = APIRouter(prefix="/desktop", tags=["desktop"])

RESTORE_FILE = "restore-pending.db"
_MAX_BACKUP_MB = 2000


class DesktopSettingsOut(BaseModel):
    ai_key_set: bool  # never the key itself
    data_dir: str  # where the library lives on this computer
    restore_pending: bool  # a backup is waiting to replace the library at the next start
    app_version: str | None = None  # the installed CaseLens version (from the app)


class AiKeyIn(BaseModel):
    key: str = Field("", max_length=300)  # empty removes it


def _data_dir() -> Path:
    folder = get_settings().caselens_data_dir
    if not folder:
        raise HTTPException(500, "The app's folder is not set.")
    return Path(folder)


@router.get("/settings", response_model=DesktopSettingsOut)
def desktop_settings() -> DesktopSettingsOut:
    folder = _data_dir()
    return DesktopSettingsOut(
        ai_key_set=bool(get_settings().gemini_api_key),
        data_dir=str(folder),
        restore_pending=(folder / RESTORE_FILE).exists(),
        app_version=os.environ.get("CASELENS_APP_VERSION"),
    )


@router.put("/ai-key", response_model=DesktopSettingsOut)
def set_ai_key(body: AiKeyIn) -> DesktopSettingsOut:
    """Keep the client's AI key in the computer's password store. New digests and questions use it at once."""
    save_ai_key(str(_data_dir()), body.key.strip() or None)
    get_settings.cache_clear()  # the next request reads the new key
    return desktop_settings()


@router.get("/backup")
def backup(background: BackgroundTasks) -> FileResponse:
    """A copy of the whole library (cases, digests, uploads, edits) as one file, made safely while the app runs."""
    target = Path(tempfile.mkdtemp()) / f"caselens-backup-{date.today().isoformat()}.db"
    raw = engine.raw_connection()  # VACUUM cannot run inside a transaction; the driver connection is in autocommit mode
    try:
        raw.driver_connection.execute("VACUUM INTO ?", (str(target),))
    finally:
        raw.close()
    background.add_task(target.unlink, missing_ok=True)
    return FileResponse(target, filename=target.name, media_type="application/vnd.sqlite3")


@router.post("/restore", response_model=DesktopSettingsOut)
def restore(file: UploadFile) -> DesktopSettingsOut:
    """Take a backup file; it replaces the library the next time CaseLens starts (a library in use cannot be swapped)."""
    folder = _data_dir()
    pending = folder / RESTORE_FILE
    with tempfile.NamedTemporaryFile(delete=False, dir=folder, suffix=".db") as out:
        size = 0
        while chunk := file.file.read(1024 * 1024):
            size += len(chunk)
            if size > _MAX_BACKUP_MB * 1024 * 1024:
                Path(out.name).unlink(missing_ok=True)
                raise HTTPException(413, "That file is too large to be a CaseLens backup.")
            out.write(chunk)
    candidate = Path(out.name)
    if not _is_caselens_backup(candidate):
        candidate.unlink(missing_ok=True)
        raise HTTPException(400, "That file is not a CaseLens backup.")
    candidate.replace(pending)
    return desktop_settings()


def _is_caselens_backup(path: Path) -> bool:
    try:
        with sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True) as connection:
            tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    except sqlite3.DatabaseError:
        return False
    return {"cases", "subjects", "alembic_version"} <= tables
