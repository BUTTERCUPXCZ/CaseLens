# PyInstaller recipe for the desktop app's backend: `pyinstaller caselens.spec` (run in backend/, after `npm run build` in
# frontend/ and with catalog.sqlite present). Output: dist/caselens-server/ (one folder: starts fast, fewer antivirus alarms).
from PyInstaller.utils.hooks import collect_all, collect_submodules

datas = [
    ("caselens/infrastructure/db/sqlite_migrations", "caselens/infrastructure/db/sqlite_migrations"),  # read by Alembic as files
    ("../frontend/dist", "frontend"),
    ("catalog.sqlite", "."),
]
binaries = []
_WEB_ONLY = ("caselens.infrastructure.queue.actors", "caselens.infrastructure.queue.broker", "caselens.infrastructure.queue.rabbit_job_queue")
hiddenimports = collect_submodules("caselens", filter=lambda name: name not in _WEB_ONLY) + collect_submodules("uvicorn") + ["sqlalchemy.dialects.sqlite"]
for package in ("docx", "keyring", "google.genai", "fitz", "pymupdf", "selectolax"):
    package_datas, package_binaries, package_imports = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_imports

analysis = Analysis(
    ["desktop_entry.py"],
    pathex=["."],
    datas=datas,
    binaries=binaries,
    hiddenimports=hiddenimports,
    excludes=["dramatiq", "pika", "psycopg", "psycopg_binary", "pytest", "tkinter"],  # the web version's queue and database
)
pyz = PYZ(analysis.pure)
exe = EXE(pyz, analysis.scripts, [], exclude_binaries=True, name="caselens-server", console=False, upx=False)
COLLECT(exe, analysis.binaries, analysis.datas, name="caselens-server", upx=False)
