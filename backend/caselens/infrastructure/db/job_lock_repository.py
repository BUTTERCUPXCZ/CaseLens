from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.engine import Engine

from caselens.application.ports.locks import JobLockRepository
from caselens.infrastructure.db.orm_models import JobLockModel

_LOCKS = JobLockModel.__table__


class SqlJobLockRepository(JobLockRepository):
    """Locks in the database (PostgreSQL for the web version, SQLite for the desktop app). Each call runs in its own short
    transaction on a separate connection, so the answer is final and visible to the API and to every worker immediately."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self._insert = postgresql.insert if engine.dialect.name == "postgresql" else sqlite.insert

    def acquire(self, key: str, ttl_seconds: int) -> bool:
        # One atomic statement: a row comes back only when the caller got the lock (a new key, or a lock whose time has run out).
        now = datetime.now(UTC)
        until = now + timedelta(seconds=ttl_seconds)
        statement = (
            self._insert(_LOCKS)
            .values(key=key, locked_until=until, created_at=now)
            .on_conflict_do_update(
                index_elements=[_LOCKS.c.key],
                set_={"locked_until": until, "created_at": now},
                where=_LOCKS.c.locked_until < now,
            )
            .returning(_LOCKS.c.key)
        )
        with self._engine.begin() as connection:
            return connection.execute(statement).first() is not None

    def release(self, key: str) -> None:
        with self._engine.begin() as connection:
            connection.execute(delete(_LOCKS).where(_LOCKS.c.key == key))

    def release_all(self) -> None:
        with self._engine.begin() as connection:
            connection.execute(delete(_LOCKS))

    def is_held(self, key: str) -> bool:
        with self._engine.begin() as connection:
            held = select(_LOCKS.c.key).where(_LOCKS.c.key == key, _LOCKS.c.locked_until > datetime.now(UTC))
            return connection.execute(held).first() is not None
