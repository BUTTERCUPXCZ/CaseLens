"""The desktop app's backend: the API and the built screens from one local address, with the library in a SQLite file.

The desktop shell starts it as `caselens-server --port 51234 --data-dir <folder>` and opens http://127.0.0.1:51234/."""
import argparse
import logging
import os
import shutil
import sys
from pathlib import Path

log = logging.getLogger("caselens.desktop")

_LOCAL_HOSTS = {"127.0.0.1", "localhost"}
_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def bundled_path(name: str) -> Path:
    """A file shipped with the program: inside the PyInstaller bundle, or in the repository when run from source."""
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / name
    return Path(__file__).resolve().parents[3] / {"frontend": "frontend/dist", "catalog.sqlite": "backend/catalog.sqlite"}[name]


def apply_pending_restore(data_dir: Path) -> bool:
    """A backup chosen in Settings replaces the library here, before anything opens it. The old library is kept beside it."""
    from caselens.desktop.api import RESTORE_FILE

    pending = data_dir / RESTORE_FILE
    if not pending.exists():
        return False
    for suffix in ("", "-wal", "-shm"):  # the -wal file may hold the last changes: it moves with the old library
        old = data_dir / f"caselens.db{suffix}"
        if old.exists():
            shutil.move(old, data_dir / f"caselens-before-restore.db{suffix}")
    pending.replace(data_dir / "caselens.db")
    log.info("Library restored from a backup")
    return True


def create_desktop_app(frontend_dir: Path):
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse
    from starlette.exceptions import HTTPException as StarletteHTTPException
    from starlette.staticfiles import StaticFiles

    from caselens.desktop import api as desktop_api
    from caselens.main import _lifespan, create_app

    class ScreenFiles(StaticFiles):
        """The built screens; any unknown path (a page like /library) gets index.html so the screen's router shows it."""

        async def get_response(self, path, scope):
            try:
                return await super().get_response(path, scope)
            except StarletteHTTPException as exc:
                if exc.status_code != 404 or path.startswith("assets/"):
                    raise
                return await super().get_response("index.html", scope)

    api = create_app()
    api.include_router(desktop_api.router)
    root = FastAPI(lifespan=_lifespan, docs_url=None, redoc_url=None, openapi_url=None)  # mounted apps do not run their own

    @root.middleware("http")
    async def only_this_computer(request: Request, call_next):
        """Other websites open in a browser on the same computer must not reach the library: the address must be this
        computer by name (stops DNS rebinding), and changes must come from the app's own page (stops cross-site forms)."""
        host = (request.headers.get("host") or "").rsplit(":", 1)[0]
        if host not in _LOCAL_HOSTS:
            return JSONResponse({"detail": "Not allowed."}, status_code=403)
        # Browsers say where a request comes from: only the app's own page (same address and port) may use the library.
        if request.headers.get("sec-fetch-site", "same-origin") not in ("same-origin", "none"):
            return JSONResponse({"detail": "Not allowed."}, status_code=403)
        own_origin = f"http://{request.headers.get('host')}"
        if request.method not in _SAFE_METHODS and request.headers.get("origin") != own_origin:
            return JSONResponse({"detail": "Not allowed."}, status_code=403)
        return await call_next(request)

    root.mount("/api", api)
    root.mount("/", ScreenFiles(directory=frontend_dir, html=True), name="screens")
    return root


def _log_to_file(data_dir: Path) -> None:
    """The packaged program has no console window (on Windows its output goes nowhere), so the log is a file in the app's
    folder: logs/server.log, the last run only, for when something needs explaining."""
    logs = data_dir / "logs"
    logs.mkdir(exist_ok=True)
    stream = open(logs / "server.log", "w", encoding="utf-8", buffering=1)  # noqa: SIM115 - open for the program's whole life
    if sys.stdout is None or getattr(sys, "frozen", False):
        sys.stdout = sys.stderr = stream
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s", handlers=[logging.StreamHandler(stream)])


def _stop_with_the_app(app_pid: int) -> None:
    """If the window program ends in any way (closed, crashed, killed), this backend ends too instead of running on unseen."""
    import threading

    def watch() -> None:
        if sys.platform == "win32":
            import ctypes

            synchronize, infinite = 0x00100000, 0xFFFFFFFF
            handle = ctypes.windll.kernel32.OpenProcess(synchronize, False, app_pid)
            if handle:
                ctypes.windll.kernel32.WaitForSingleObject(handle, infinite)
        else:
            import time

            while os.getppid() == app_pid:  # the app's child: a new parent means the app is gone
                time.sleep(2)
        log.info("The app closed; stopping")
        os._exit(0)

    threading.Thread(target=watch, daemon=True, name="app-watch").start()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="caselens-server")
    parser.add_argument("--port", type=int, default=int(os.environ.get("CASELENS_PORT", "8765")))
    parser.add_argument("--data-dir", default=os.environ.get("CASELENS_DATA_DIR"), required="CASELENS_DATA_DIR" not in os.environ)
    parser.add_argument("--frontend-dir", default=os.environ.get("CASELENS_FRONTEND_DIR"))
    parser.add_argument("--app-pid", type=int, help="the window program; this backend stops when it ends")
    args = parser.parse_args(argv)
    data_dir = Path(args.data_dir).expanduser().resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    _log_to_file(data_dir)
    if args.app_pid:
        _stop_with_the_app(args.app_pid)
    frontend_dir = Path(args.frontend_dir).resolve() if args.frontend_dir else bundled_path("frontend")
    os.chdir(data_dir)  # settings read a .env from the working folder: only the app's own folder counts, never a stray one
    # Settings and the database engine are read when caselens modules load, so these come first.
    os.environ["CASELENS_DESKTOP"] = "1"
    os.environ["CASELENS_DATA_DIR"] = str(data_dir)
    os.environ["DATABASE_URL"] = f"sqlite:///{(data_dir / 'caselens.db').as_posix()}"
    apply_pending_restore(data_dir)

    import uvicorn

    from caselens.desktop.catalog_seed import import_catalog
    from caselens.infrastructure.config import get_settings
    from caselens.infrastructure.db.session import engine
    from caselens.infrastructure.db.sqlite_schema import upgrade_sqlite

    upgrade_sqlite(get_settings().database_url)
    import_catalog(engine, Path(os.environ.get("CASELENS_CATALOG_SEED") or bundled_path("catalog.sqlite")))
    uvicorn.run(create_desktop_app(frontend_dir), host="127.0.0.1", port=args.port, log_level="info", log_config=None)


if __name__ == "__main__":
    main()
