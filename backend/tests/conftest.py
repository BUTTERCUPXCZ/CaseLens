"""Database tests run on their own database (`caselens_test`), never the dev one: PostgreSQL (the web version) or, with a
`sqlite:///...` DATABASE_URL, a fresh SQLite file (the desktop app), so both databases are tested by the same tests.

The schema is built by the real Alembic migrations, so a test failure also catches a
broken migration. Each test runs inside a transaction that is rolled back.
"""
import os
from collections.abc import Iterator
from pathlib import Path

# Tests never talk to a real broker unless a test asks for one: Dramatiq keeps messages in memory.
os.environ.setdefault("QUEUE_BACKEND", "stub")

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session

from caselens.infrastructure.config import get_settings

BACKEND_DIR = Path(__file__).resolve().parent.parent
TEST_DB_NAME = "caselens_test"


def _sqlite_test_engine(dev_url) -> Engine:
    """The desktop app's database: a fresh SQLite file next to the dev one, built by the desktop migrations."""
    from caselens.infrastructure.db.session import make_engine
    from caselens.infrastructure.db.sqlite_schema import upgrade_sqlite

    folder = Path(dev_url.database).resolve().parent if dev_url.database else Path(".")
    path = folder / "caselens_test.db"
    for leftover in (path, path.with_name(path.name + "-wal"), path.with_name(path.name + "-shm")):
        leftover.unlink(missing_ok=True)
    url = f"sqlite:///{path.as_posix()}"
    upgrade_sqlite(url)
    return make_engine(url)


@pytest.fixture(scope="session")
def test_engine() -> Iterator[Engine]:
    dev_url = make_url(get_settings().database_url)
    if dev_url.get_backend_name() == "sqlite":
        engine = _sqlite_test_engine(dev_url)
        yield engine
        engine.dispose()
        return
    admin = create_engine(dev_url, isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        exists = connection.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": TEST_DB_NAME}
        )
        if not exists:
            connection.execute(text(f'CREATE DATABASE "{TEST_DB_NAME}"'))
    admin.dispose()

    engine = create_engine(dev_url.set(database=TEST_DB_NAME))
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(test_engine: Engine) -> Iterator[Session]:
    """A session whose work is rolled back afterwards, even if the code under test
    calls commit() (it only releases a SAVEPOINT inside the outer transaction)."""
    connection = test_engine.connect()
    outer = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        outer.rollback()
        connection.close()


@pytest.fixture
def postgres_only(test_engine: Engine) -> None:
    """For tests of PostgreSQL-only features (row-level security, the web version's migrations, its query plans)."""
    if test_engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL only: the desktop app's SQLite database has no such feature")
