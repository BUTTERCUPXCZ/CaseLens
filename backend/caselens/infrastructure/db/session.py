from collections.abc import Iterator

from sqlalchemy import Engine, create_engine, event, make_url
from sqlalchemy.orm import Session, sessionmaker

from caselens.infrastructure.config import get_settings

def _connect_args(url: str) -> dict:
    """A hosted database (Supabase) needs an encrypted connection; the local Docker one does not.

    `require` encrypts but does not check the server's certificate. For that, put `?sslmode=verify-full` (and
    `sslrootcert=<path to the provider's CA file>`) in DATABASE_URL: a sslmode already in the URL is never overridden."""
    parsed = make_url(url)
    if "sslmode" in parsed.query:
        return {}
    return {} if (parsed.host or "") in ("localhost", "127.0.0.1", "db", "") else {"sslmode": "require"}


def _sqlite_connect_args() -> dict:
    # The desktop app: the API and its background threads share one database file.
    return {"check_same_thread": False, "timeout": 30}


def _on_sqlite_connect(connection, _record) -> None:
    """Write-ahead logging lets the API read while a background job writes; foreign keys are off by default in SQLite. The
    driver's own transaction handling is turned off so SQLAlchemy's BEGIN and SAVEPOINT work as they do on PostgreSQL."""
    connection.isolation_level = None
    cursor = connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.close()


def _on_sqlite_begin(connection) -> None:
    connection.exec_driver_sql("BEGIN")


def make_engine(url: str) -> Engine:
    """PostgreSQL for the web version, a SQLite file for the desktop app."""
    if make_url(url).get_backend_name() == "sqlite":
        # 12 digest threads, 2 question threads and the page's own requests each hold a connection while they work.
        sqlite_engine = create_engine(url, connect_args=_sqlite_connect_args(), pool_size=20, max_overflow=20)
        event.listen(sqlite_engine, "connect", _on_sqlite_connect)
        event.listen(sqlite_engine, "begin", _on_sqlite_begin)
        return sqlite_engine
    return create_engine(url, pool_pre_ping=True, connect_args=_connect_args(url))


engine = make_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """One database session per unit of work (request or job)."""
    with SessionLocal() as session:
        yield session
