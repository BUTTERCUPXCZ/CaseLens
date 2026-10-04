from abc import ABC, abstractmethod


class JobLockRepository(ABC):
    """"Only one at a time" for background work: one catalog build, one fetch per case, one AI run per digest.

    A lock always has a time limit, so a worker that crashes cannot block the work forever. Taking and
    releasing are visible to every process at once (they do not wait for the caller's own unit of work).
    """

    @abstractmethod
    def acquire(self, key: str, ttl_seconds: int) -> bool:
        """True if the caller now holds the lock (it was free, or its time had run out). False if someone holds it."""

    @abstractmethod
    def release(self, key: str) -> None: ...

    @abstractmethod
    def is_held(self, key: str) -> bool: ...

    @abstractmethod
    def release_all(self) -> None:
        """Free every lock. Only for a restart of a single-process host, when nothing from before can still be running."""
