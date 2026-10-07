"""The client's AI keys (one per provider: Gemini, Groq, DeepSeek), kept in the computer's password store (Windows Credential
Manager, the Mac Keychain). They are never written to the database or shown back. Where no password store works (some Linux
setups), each falls back to a file only the user can read. The chosen provider is a small file in the app's folder."""
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

_SERVICE = "CaseLens"
_PROVIDERS = ("gemini", "groq", "deepseek", "openrouter")
_PROVIDER_FILE = "ai-provider.txt"


def _account(provider: str) -> str:
    return f"{provider}-api-key"  # "gemini-api-key" is the name the first versions used: an existing key keeps working


def _fallback(data_dir: str | None, provider: str) -> Path | None:
    if not data_dir:
        return None
    return Path(data_dir) / ("ai-key.txt" if provider == "gemini" else f"ai-key-{provider}.txt")


def read_ai_key(data_dir: str | None, provider: str = "gemini") -> str | None:
    try:
        import keyring

        key = keyring.get_password(_SERVICE, _account(provider))
        if key:
            return key
    except Exception:  # noqa: BLE001  no password store on this computer
        logger.info("password store not available; using the key file")
    path = _fallback(data_dir, provider)
    if path and path.exists():
        return path.read_text(encoding="utf-8").strip() or None
    return None


def save_ai_key(data_dir: str | None, key: str | None, provider: str = "gemini") -> None:
    """Keep the key (None removes it)."""
    try:
        import keyring

        if key:
            keyring.set_password(_SERVICE, _account(provider), key)
        else:
            try:
                keyring.delete_password(_SERVICE, _account(provider))
            except Exception:  # noqa: BLE001  nothing was stored
                pass
        path = _fallback(data_dir, provider)
        if path and path.exists():
            path.unlink()  # a key once kept in the file is moved to the password store
        return
    except Exception:  # noqa: BLE001
        logger.info("password store not available; keeping the key in a private file")
    path = _fallback(data_dir, provider)
    if path is None:
        raise RuntimeError("No place to keep the key.")
    if key:
        # Created private (owner only) from the start, never readable by others even for a moment.
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        os.chmod(path, 0o600)  # an older file keeps its old mode on open: make it private too
        with os.fdopen(descriptor, "w", encoding="utf-8") as out:
            out.write(key)
    elif path.exists():
        path.unlink()


_OPENROUTER_MODEL_FILE = "openrouter-model.txt"
_ONLY_CHOSEN_FILE = "ai-only-chosen.txt"


def read_openrouter_model(data_dir: str | None) -> str | None:
    """The OpenRouter model chosen in Settings (one of `OPENROUTER_MODELS`), or None for the default."""
    from caselens.infrastructure.ai.models import openrouter_model

    path = Path(data_dir) / _OPENROUTER_MODEL_FILE if data_dir else None
    if path and path.exists():
        chosen = path.read_text(encoding="utf-8").strip()
        return chosen if openrouter_model(chosen) else None
    return None


def save_openrouter_model(data_dir: str, model_id: str) -> None:
    from caselens.infrastructure.ai.models import openrouter_model

    if openrouter_model(model_id) is None:
        raise ValueError(f"Unknown OpenRouter model: {model_id}")
    (Path(data_dir) / _OPENROUTER_MODEL_FILE).write_text(model_id, encoding="utf-8")


def read_only_chosen(data_dir: str | None) -> bool:
    """Only the chosen AI writes (no other AI takes over): on unless the client turned it off."""
    path = Path(data_dir) / _ONLY_CHOSEN_FILE if data_dir else None
    return not (path and path.exists() and path.read_text(encoding="utf-8").strip() == "0")


def save_only_chosen(data_dir: str, only: bool) -> None:
    (Path(data_dir) / _ONLY_CHOSEN_FILE).write_text("1" if only else "0", encoding="utf-8")


def read_provider(data_dir: str | None) -> str | None:
    path = Path(data_dir) / _PROVIDER_FILE if data_dir else None
    if path and path.exists():
        chosen = path.read_text(encoding="utf-8").strip()
        return chosen if chosen in _PROVIDERS else None
    return None


def save_provider(data_dir: str, provider: str) -> None:
    if provider not in _PROVIDERS:
        raise ValueError(f"Unknown AI provider: {provider}")
    (Path(data_dir) / _PROVIDER_FILE).write_text(provider, encoding="utf-8")
