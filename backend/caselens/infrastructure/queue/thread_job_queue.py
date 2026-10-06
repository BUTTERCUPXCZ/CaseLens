import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from caselens.application.ports.gateways import JobQueue
from caselens.application.ports.locks import JobLockRepository
from caselens.infrastructure.queue import jobs, lock_keys

logger = logging.getLogger(__name__)


class ThreadJobQueue(JobQueue):
    """Runs the jobs as threads inside the API process: for a host with no separate workers (a free web service).

    Same rules as `RabbitJobQueue`: one lawphil thread (so "1 request per second" holds), digest threads, two question threads,
    and "only one at a time" locks kept in PostgreSQL. There is no retry and no message that survives a restart:
    work that was running when the process stopped is found again by `recovery.requeue_unfinished_work`."""

    def __init__(self, locks: JobLockRepository, *, digest_threads: int = 4) -> None:
        self._locks = locks
        self._lawphil = ThreadPoolExecutor(max_workers=1, thread_name_prefix="lawphil")
        self._digests = ThreadPoolExecutor(max_workers=digest_threads, thread_name_prefix="digests")
        # Questions have their own line: a student's question is answered in seconds even while a bulk upload's digests run.
        self._questions = ThreadPoolExecutor(max_workers=2, thread_name_prefix="questions")

    def enqueue_resolve_upload(self, upload_id: int) -> None:
        self._run(self._lawphil, jobs.resolve_upload, upload_id)

    def enqueue_fetch_case(self, gr_no: str, year: int | None) -> None:
        key = lock_keys.fetch_case_key(gr_no, year)
        if self._locks.acquire(key, lock_keys.FETCH_LOCK_SECONDS):
            self._run(self._lawphil, jobs.fetch_case, gr_no, year, lock=key, free_on_failure=True)

    def enqueue_build_digest(self, digest_id: int, keys: list[str] | None = None) -> None:
        key = lock_keys.build_digest_key(digest_id, keys)
        if self._locks.acquire(key, lock_keys.DIGEST_LOCK_SECONDS):
            self._run(self._digests, jobs.build_digest, digest_id, keys, lock=key, free_on_failure=True)

    def enqueue_bulk_item(self, item_id: int) -> None:
        self._run(self._lawphil, jobs.resolve_bulk_item, item_id)

    def enqueue_case_digest(self, digest_id: int) -> None:
        key = lock_keys.case_digest_key(digest_id)
        if self._locks.acquire(key, lock_keys.CASE_DIGEST_LOCK_SECONDS):
            self._run(self._digests, jobs.build_case_digest, digest_id, lock=key, free_on_failure=True)

    def enqueue_case_question(self, question_id: int) -> None:
        self._run(self._questions, jobs.answer_case_question, question_id)

    def enqueue_refresh_catalog(self) -> bool:
        if not self._locks.acquire(lock_keys.CATALOG_REFRESH_KEY, lock_keys.CATALOG_REFRESH_LOCK_SECONDS):
            return False
        self._run(self._lawphil, jobs.refresh_catalog, lock=lock_keys.CATALOG_REFRESH_KEY, free_on_failure=True)
        return True

    def enqueue_build_catalog(self, first_year: int) -> bool:
        if not self._locks.acquire(lock_keys.CATALOG_BUILD_KEY, lock_keys.CATALOG_BUILD_LOCK_SECONDS):
            return False
        self._run(self._lawphil, jobs.build_catalog, first_year, lock=lock_keys.CATALOG_BUILD_KEY, free_on_failure=True)
        return True

    def _run(
        self,
        pool: ThreadPoolExecutor,
        job: Callable[..., None],
        *args: object,
        lock: str | None = None,
        free_on_failure: bool = False,
    ) -> None:
        """Run `job` on a pool. A failure is logged, never raised into the pool. A lock the job does not free
        itself (fetch, refresh) is kept until its time runs out, like in the RabbitMQ version; if the job fails
        before doing any work the lock is freed so the caller can ask again."""

        def task() -> None:
            try:
                job(*args)
            except Exception:
                logger.exception("background job %s failed", job.__name__)
                if lock is not None and free_on_failure:
                    self._locks.release(lock)

        pool.submit(task)
