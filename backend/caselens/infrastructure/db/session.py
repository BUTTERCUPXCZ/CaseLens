from collections.abc import Iterator

from sqlalchemy import create_engine, make_url
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


_url = get_settings().database_url
engine = create_engine(_url, pool_pre_ping=True, connect_args=_connect_args(_url))
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """One database session per unit of work (request or job)."""
    with SessionLocal() as session:
        yield session
