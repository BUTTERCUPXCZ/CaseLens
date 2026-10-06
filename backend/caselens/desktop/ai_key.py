"""The client's AI key, kept in the computer's password store (Windows Credential Manager, the Mac Keychain). It is never written
to the database or shown back. Where no password store works (some Linux setups), it falls back to a file only the user can read."""
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

_SERVICE = "CaseLens"
_ACCOUNT = "gemini-api-key"
_FILE = "ai-key.txt"


def _fallback(data_dir: str | None) -> Path | None:
    return Path(data_dir) / _FILE if data_dir else None


def read_ai_key(data_dir: str | None) -> str | None:
    try:
        import keyring

        key = keyring.get_password(_SERVICE, _ACCOUNT)
        if key:
            return key
    except Exception:  # noqa: BLE001  no password store on this computer
        logger.info("password store not available; using the key file")
    path = _fallback(data_dir)
    if path and path.exists():
        return path.read_text(encoding="utf-8").strip() or None
    return None


def save_ai_key(data_dir: str | None, key: str | None) -> None:
    """Keep the key (None removes it)."""
    try:
        import keyring

        if key:
            keyring.set_password(_SERVICE, _ACCOUNT, key)
        else:
            try:
                keyring.delete_password(_SERVICE, _ACCOUNT)
            except Exception:  # noqa: BLE001  nothing was stored
                pass
        path = _fallback(data_dir)
        if path and path.exists():
            path.unlink()  # a key once kept in the file is moved to the password store
        return
    except Exception:  # noqa: BLE001
        logger.info("password store not available; keeping the key in a private file")
    path = _fallback(data_dir)
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
