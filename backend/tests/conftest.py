"""Database tests run on their own database (`caselens_test`), never the dev one.

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


@pytest.fixture(scope="session")
def test_engine() -> Iterator[Engine]:
    dev_url = make_url(get_settings().database_url)
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
