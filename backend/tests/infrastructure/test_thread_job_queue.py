"""ThreadJobQueue: the right job with the right arguments, "only one at a time" holds, a failing job is logged
and never breaks the pool, and a lock is freed when a job fails before doing any work."""
import pytest

from caselens.infrastructure.queue import jobs, lock_keys
from caselens.infrastructure.queue.thread_job_queue import ThreadJobQueue
from tests.fakes import InMemoryJobLocks


@pytest.fixture
def calls(monkeypatch):
    seen: list[tuple] = []
    for name in ("resolve_upload", "fetch_case", "build_digest", "refresh_catalog", "build_catalog"):
        monkeypatch.setattr(jobs, name, lambda *a, _n=name: seen.append((_n, *a)))
        getattr(jobs, name).__name__ = name
    return seen


@pytest.fixture
def locks():
    return InMemoryJobLocks()


@pytest.fixture
def queue(locks):
    return ThreadJobQueue(locks)


def finish(queue: ThreadJobQueue) -> None:
    queue._lawphil.shutdown(wait=True)
    queue._digests.shutdown(wait=True)
    queue._questions.shutdown(wait=True)


def test_each_job_runs_with_its_arguments(queue, calls):
    queue.enqueue_resolve_upload(5)
    queue.enqueue_fetch_case("180046", 2009)
    queue.enqueue_build_digest(7, ["topic"])
    assert queue.enqueue_build_catalog(1987) is True
    assert queue.enqueue_refresh_catalog() is True
    finish(queue)
    assert sorted(calls, key=str) == sorted(
        [
            ("resolve_upload", 5),
            ("fetch_case", "180046", 2009),
            ("build_digest", 7, ["topic"]),
            ("build_catalog", 1987),
            ("refresh_catalog",),
        ],
        key=str,
    )


def test_the_same_work_asked_twice_is_queued_once(queue, calls):
    queue.enqueue_fetch_case("1", None)
    queue.enqueue_fetch_case("1", None)
    queue.enqueue_build_digest(3)
    queue.enqueue_build_digest(3)
    assert queue.enqueue_build_catalog(1987) is True
    assert queue.enqueue_build_catalog(1987) is False
    finish(queue)
    assert len([c for c in calls if c[0] == "fetch_case"]) == 1
    assert len([c for c in calls if c[0] == "build_digest"]) == 1
    assert len([c for c in calls if c[0] == "build_catalog"]) == 1


def test_a_failing_job_frees_its_lock_and_does_not_stop_the_next_job(queue, locks, monkeypatch, calls):
    def boom(*_):
        raise RuntimeError("network down")

    boom.__name__ = "fetch_case"
    monkeypatch.setattr(jobs, "fetch_case", boom)
    queue.enqueue_fetch_case("9", 2001)
    queue.enqueue_resolve_upload(1)  # the same one-thread pool keeps working
    finish(queue)
    assert locks.is_held(lock_keys.fetch_case_key("9", 2001)) is False
    assert ("resolve_upload", 1) in calls


def test_a_question_is_answered_even_while_every_digest_thread_is_busy(monkeypatch, locks):
    """During a bulk upload all digest threads are busy for minutes; a student's question must not wait behind them."""
    import threading

    release, answered = threading.Event(), threading.Event()
    monkeypatch.setattr(jobs, "build_case_digest", lambda *_: release.wait(5))
    monkeypatch.setattr(jobs, "answer_case_question", lambda *_: answered.set())
    queue = ThreadJobQueue(locks, digest_threads=2)
    for digest_id in (1, 2, 3):
        queue.enqueue_case_digest(digest_id)
    queue.enqueue_case_question(9)
    try:
        assert answered.wait(2)  # answered while the digests still run
    finally:
        release.set()
        finish(queue)


def test_the_desktop_app_writes_twelve_digests_at_once_and_the_website_four(tmp_path):
    from caselens.infrastructure.config import Settings

    assert Settings(_env_file=None, database_url="sqlite:///x.db").digest_threads == 4
    desktop = Settings(_env_file=None, caselens_desktop=True, caselens_data_dir=str(tmp_path), gemini_api_key="k")
    assert desktop.digest_threads == 12
    assert Settings(_env_file=None, caselens_desktop=True, caselens_data_dir=str(tmp_path), gemini_api_key="k", digest_threads=6).digest_threads == 6
