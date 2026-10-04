from typing import Protocol

import dramatiq
from dramatiq.errors import BrokerConnectionError
from pika.exceptions import AMQPError

from caselens.application.ports.gateways import JobQueue
from caselens.application.ports.locks import JobLockRepository
from caselens.domain.errors import JobQueueUnavailableError
from caselens.infrastructure.queue import lock_keys


class Actors(Protocol):
    """The five background jobs (see `actors.py`). A test passes stand-ins; production passes the module."""

    resolve_upload: dramatiq.Actor
    fetch_case: dramatiq.Actor
    build_catalog: dramatiq.Actor
    refresh_catalog: dramatiq.Actor
    build_digest: dramatiq.Actor


class RabbitJobQueue(JobQueue):
    """Hands work to RabbitMQ. Jobs that must not run twice take a lock first (kept in PostgreSQL, because a
    message broker has no "only one at a time"); if RabbitMQ cannot be reached the lock is given back, so it
    is not stuck, and the caller gets a clear `JobQueueUnavailableError` (HTTP 503)."""

    def __init__(self, locks: JobLockRepository, actors: Actors) -> None:
        self._locks = locks
        self._actors = actors

    def enqueue_resolve_upload(self, upload_id: int) -> None:
        self._send(self._actors.resolve_upload, upload_id)

    def enqueue_fetch_case(self, gr_no: str, year: int | None) -> None:
        key = lock_keys.fetch_case_key(gr_no, year)
        if self._locks.acquire(key, lock_keys.FETCH_LOCK_SECONDS):
            self._send(self._actors.fetch_case, gr_no, year, lock=key)  # else: already queued or running

    def enqueue_build_digest(self, digest_id: int, keys: list[str] | None = None) -> None:
        key = lock_keys.build_digest_key(digest_id, keys)
        if self._locks.acquire(key, lock_keys.DIGEST_LOCK_SECONDS):
            self._send(self._actors.build_digest, digest_id, keys, lock=key)  # else: the AI is already working on it

    def enqueue_refresh_catalog(self) -> bool:
        if not self._locks.acquire(lock_keys.CATALOG_REFRESH_KEY, lock_keys.CATALOG_REFRESH_LOCK_SECONDS):
            return False
        self._send(self._actors.refresh_catalog, lock=lock_keys.CATALOG_REFRESH_KEY)
        return True

    def enqueue_build_catalog(self, first_year: int) -> bool:
        if not self._locks.acquire(lock_keys.CATALOG_BUILD_KEY, lock_keys.CATALOG_BUILD_LOCK_SECONDS):
            return False  # a build is already queued or running
        self._send(self._actors.build_catalog, first_year, lock=lock_keys.CATALOG_BUILD_KEY)
        return True

    def _send(self, actor: dramatiq.Actor, *args: object, lock: str | None = None) -> None:
        try:
            actor.send(*args)
        except (BrokerConnectionError, AMQPError, OSError) as exc:
            if lock is not None:
                self._locks.release(lock)
            raise JobQueueUnavailableError("The job queue is not reachable right now. Try again in a moment.") from exc
