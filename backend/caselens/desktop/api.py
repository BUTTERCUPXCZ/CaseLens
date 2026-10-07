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

from caselens.desktop.ai_key import save_ai_key, save_only_chosen, save_openrouter_model, save_provider
from caselens.infrastructure.ai.models import OPENROUTER_MODELS, openrouter_model
from caselens.infrastructure.ai.calls import PROVIDER_NAMES, PROVIDERS, ai_configured, api_key_for, forget_key_problem, key_problem, model_name
from caselens.infrastructure.ai.gemini_answerer import check_gemini_key
from caselens.infrastructure.ai.openai_style_call import check_key
from caselens.infrastructure.config import get_settings
from caselens.infrastructure.db.session import engine

router = APIRouter(prefix="/desktop", tags=["desktop"])

RESTORE_FILE = "restore-pending.db"
_MAX_BACKUP_MB = 2000


class ProviderOut(BaseModel):
    id: str  # groq | deepseek | gemini
    name: str
    model: str  # the model that writes
    key_set: bool  # never the key itself
    problem: str | None = None  # "invalid" | "credit": its last call was refused for the key itself


class OpenRouterModelOut(BaseModel):
    id: str
    name: str
    free: bool


class DesktopSettingsOut(BaseModel):
    ai_key_set: bool  # any provider has a key (never the key itself)
    data_dir: str  # where the library lives on this computer
    restore_pending: bool  # a backup is waiting to replace the library at the next start
    app_version: str | None = None  # the installed CaseLens version (from the app)
    ai_out_of_credit: bool = False  # the key's last AI call was refused for no credit / no allowance left
    ai_key_invalid: bool = False  # the key's last AI call was refused because the key itself is not valid
    ai_provider: str = "gemini"  # the provider that writes first; the others with a key take over when it cannot answer
    providers: list[ProviderOut] = []
    ai_only_chosen: bool = False  # only the chosen AI writes: no other AI takes over when it cannot answer
    openrouter_model: str = ""  # the OpenRouter model that writes and checks
    openrouter_models: list[OpenRouterModelOut] = []  # the ones the client can pick


class AiKeyIn(BaseModel):
    key: str = Field("", max_length=300)  # empty removes it
    provider: str = Field("gemini", pattern="^(groq|deepseek|openrouter|gemini)$")


class AiProviderIn(BaseModel):
    provider: str = Field(pattern="^(groq|deepseek|openrouter|gemini)$")


class OpenRouterModelIn(BaseModel):
    model: str = Field(max_length=200)


class OnlyChosenIn(BaseModel):
    only: bool


_KEY_HELP = {
    "gemini": "Google says this is not a valid Gemini API key. Copy it again from Google AI Studio (it starts with AIza).",
    "groq": "Groq says this is not a valid API key. Copy it again from console.groq.com → API Keys (it starts with gsk_).",
    "deepseek": "DeepSeek says this is not a valid API key. Copy it again from platform.deepseek.com → API keys (it starts with sk-).",
    "openrouter": "OpenRouter says this is not a valid API key. Copy it again from openrouter.ai → Keys (it starts with sk-or-).",
}


def _model_of(provider: str) -> str:
    return model_name(get_settings(), provider)


def _data_dir() -> Path:
    folder = get_settings().caselens_data_dir
    if not folder:
        raise HTTPException(500, "The app's folder is not set.")
    return Path(folder)


@router.get("/settings", response_model=DesktopSettingsOut)
def desktop_settings() -> DesktopSettingsOut:
    folder = _data_dir()
    settings = get_settings()
    chosen = settings.ai_provider if settings.ai_provider in PROVIDERS else "gemini"
    return DesktopSettingsOut(
        ai_key_set=ai_configured(settings),
        data_dir=str(folder),
        restore_pending=(folder / RESTORE_FILE).exists(),
        app_version=os.environ.get("CASELENS_APP_VERSION"),
        ai_out_of_credit=key_problem(chosen) == "credit",
        ai_key_invalid=key_problem(chosen) == "invalid",
        ai_provider=chosen,
        providers=[
            ProviderOut(id=p, name=PROVIDER_NAMES[p], model=_model_of(p), key_set=bool(api_key_for(settings, p)), problem=key_problem(p))
            for p in PROVIDERS
        ],
        ai_only_chosen=settings.ai_only_chosen,
        openrouter_model=settings.openrouter_model,
        openrouter_models=[OpenRouterModelOut(id=m.id, name=m.name, free=m.free) for m in OPENROUTER_MODELS],
    )


@router.put("/ai-key", response_model=DesktopSettingsOut)
def set_ai_key(body: AiKeyIn) -> DesktopSettingsOut:
    """Keep the client's AI key in the computer's password store. New digests and questions use it at once."""
    key, provider = body.key.strip(), body.provider
    works = (check_gemini_key(key) if provider == "gemini" else check_key(provider, key)) if key else None
    if works is False:  # offline or the provider down (None): saved anyway, the first digest will tell
        raise HTTPException(400, _KEY_HELP[provider])
    save_ai_key(str(_data_dir()), key or None, provider)
    get_settings.cache_clear()  # the next request reads the new key
    forget_key_problem(provider)  # a new key: the old key's problem no longer applies
    return desktop_settings()


@router.put("/ai-provider", response_model=DesktopSettingsOut)
def set_ai_provider(body: AiProviderIn) -> DesktopSettingsOut:
    """Which provider writes first. The others that have a key take over when it cannot answer."""
    save_provider(str(_data_dir()), body.provider)
    get_settings.cache_clear()
    return desktop_settings()


@router.put("/openrouter-model", response_model=DesktopSettingsOut)
def set_openrouter_model(body: OpenRouterModelIn) -> DesktopSettingsOut:
    """Which OpenRouter model writes and checks the digests. New digests use it at once."""
    if openrouter_model(body.model) is None:
        raise HTTPException(400, "That model is not one CaseLens offers.")
    save_openrouter_model(str(_data_dir()), body.model)
    get_settings.cache_clear()
    return desktop_settings()


@router.put("/ai-only-chosen", response_model=DesktopSettingsOut)
def set_only_chosen(body: OnlyChosenIn) -> DesktopSettingsOut:
    """On: only the chosen AI writes; if it cannot answer, the digest says why. Off: another AI with a key takes over."""
    save_only_chosen(str(_data_dir()), body.only)
    get_settings.cache_clear()
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
