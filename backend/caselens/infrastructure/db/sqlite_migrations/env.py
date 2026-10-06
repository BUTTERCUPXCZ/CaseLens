"""Migrations for the desktop app's SQLite database. The web version's PostgreSQL schema keeps its own history in `backend/alembic`;
SQLite starts from one baseline made from the models, and later changes use batch mode (SQLite cannot alter most columns in place)."""
from alembic import context
from sqlalchemy import create_engine

from caselens.infrastructure.config import get_settings
from caselens.infrastructure.db import orm_models  # noqa: F401  (registers tables)
from caselens.infrastructure.db.base import Base

config = context.config
target_metadata = Base.metadata


def _configure(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True)


supplied = config.attributes.get("connection")
if supplied is not None:
    _configure(supplied)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_engine(config.get_main_option("sqlalchemy.url") or get_settings().database_url)
    with engine.connect() as connection:
        _configure(connection)
        with context.begin_transaction():
            context.run_migrations()
