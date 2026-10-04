from sqlalchemy import text
from sqlalchemy.engine import Engine

from caselens.application.ports.locks import JobLockRepository

# One atomic statement: a row comes back only when the caller got the lock (a new key, or a lock whose time has run out).
_ACQUIRE = text(
    """
    INSERT INTO job_locks (key, locked_until)
    VALUES (:key, now() + make_interval(secs => :ttl))
    ON CONFLICT (key) DO UPDATE
        SET locked_until = EXCLUDED.locked_until, created_at = now()
        WHERE job_locks.locked_until < now()
    RETURNING key
    """
)


class SqlJobLockRepository(JobLockRepository):
    """Locks in PostgreSQL. Each call runs in its own short transaction on a separate connection, so the answer
    is final and visible to the API and to every worker immediately."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def acquire(self, key: str, ttl_seconds: int) -> bool:
        with self._engine.begin() as connection:
            return connection.execute(_ACQUIRE, {"key": key, "ttl": ttl_seconds}).first() is not None

    def release(self, key: str) -> None:
        with self._engine.begin() as connection:
            connection.execute(text("DELETE FROM job_locks WHERE key = :key"), {"key": key})

    def is_held(self, key: str) -> bool:
        with self._engine.begin() as connection:
            return connection.execute(
                text("SELECT 1 FROM job_locks WHERE key = :key AND locked_until > now()"), {"key": key}
            ).first() is not None
