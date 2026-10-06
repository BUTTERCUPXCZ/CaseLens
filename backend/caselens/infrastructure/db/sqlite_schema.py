"""Bring the desktop app's SQLite database up to date when the app starts (the web version runs `alembic upgrade head` instead)."""
from pathlib import Path

from alembic import command
from alembic.config import Config

_MIGRATIONS = Path(__file__).resolve().parent / "sqlite_migrations"


def sqlite_config(url: str) -> Config:
    config = Config()
    config.set_main_option("script_location", str(_MIGRATIONS))
    config.set_main_option("sqlalchemy.url", url)
    return config


def upgrade_sqlite(url: str) -> None:
    """Create the tables on first start; apply any newer migrations after an update. Safe to run on every start."""
    command.upgrade(sqlite_config(url), "head")
