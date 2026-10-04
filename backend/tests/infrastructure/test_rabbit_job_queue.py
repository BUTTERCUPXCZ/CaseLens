"""RabbitJobQueue against Dramatiq's in-memory broker (no RabbitMQ needed): the right job, with the right
arguments, on the right queue, and "only one at a time" really holds."""
import pytest
from dramatiq.errors import ConnectionClosed
from dramatiq.message import Message

from caselens.domain.errors import JobQueueUnavailableError
from caselens.infrastructure.queue import actors, lock_keys
from caselens.infrastructure.queue.broker import DIGEST_QUEUE, LAWPHIL_QUEUE
from caselens.infrastructure.queue.rabbit_job_queue import RabbitJobQueue
from tests.fakes import InMemoryJobLocks


@pytest.fixture
def locks():
    return InMemoryJobLocks()


@pytest.fixture
def queue(locks):
    actors.broker.flush_all()
    return RabbitJobQueue(locks, actors)


def waiting(queue_name: str) -> list[tuple[str, tuple, dict]]:
    """(actor name, args, kwargs) of the messages waiting in a queue, in order."""
    messages = [Message.decode(item) for item in list(actors.broker.queues[queue_name].queue)]
    return [(m.actor_name, tuple(m.args), dict(m.kwargs)) for m in messages]


def test_the_stub_broker_is_in_use_so_no_test_touches_a_real_one():
    assert actors.broker.__class__.__name__ == "StubBroker"


def test_an_upload_to_resolve_goes_to_the_lawphil_queue(queue):
    queue.enqueue_resolve_upload(5)
    assert waiting(LAWPHIL_QUEUE) == [("resolve_upload", (5,), {})]


def test_polling_a_search_queues_one_fetch_not_one_per_request(queue):
    for _ in range(20):  # a client polling every few seconds
        queue.enqueue_fetch_case("180046", 2009)
    assert waiting(LAWPHIL_QUEUE) == [("fetch_case", ("180046", 2009), {})]


def test_a_different_number_or_year_gets_its_own_fetch(queue):
    queue.enqueue_fetch_case("180046", 2009)
    queue.enqueue_fetch_case("180046", 2010)
    queue.enqueue_fetch_case("173931", 2009)
    assert len(waiting(LAWPHIL_QUEUE)) == 3


def test_digest_work_goes_to_the_digest_queue_and_the_same_work_is_not_queued_twice(queue):
    queue.enqueue_build_digest(7)
    queue.enqueue_build_digest(7)  # the same work: the AI must not be paid twice
    queue.enqueue_build_digest(7, ["q1"])  # different work
    assert waiting(DIGEST_QUEUE) == [("build_digest", (7, None), {}), ("build_digest", (7, ["q1"]), {})]
    assert waiting(LAWPHIL_QUEUE) == []


def test_only_one_catalog_build_at_a_time(queue, locks):
    assert queue.enqueue_build_catalog(1987) is True
    assert queue.enqueue_build_catalog(1987) is False
    assert waiting(LAWPHIL_QUEUE) == [("build_catalog", (1987,), {})]
    assert locks.is_held(lock_keys.CATALOG_BUILD_KEY)


def test_the_catalog_refresh_is_queued_once_a_day(queue):
    assert queue.enqueue_refresh_catalog() is True and queue.enqueue_refresh_catalog() is False
    assert waiting(LAWPHIL_QUEUE) == [("refresh_catalog", (), {})]


def test_a_lock_whose_time_ran_out_lets_the_work_be_queued_again(queue, locks):
    queue.enqueue_build_digest(9)
    locks.expire(lock_keys.build_digest_key(9, None))
    queue.enqueue_build_digest(9)
    assert len(waiting(DIGEST_QUEUE)) == 2


class _DownActor:
    def send(self, *args):
        raise ConnectionClosed("RabbitMQ is down (simulated)")


class _DownActors:
    resolve_upload = fetch_case = build_catalog = refresh_catalog = build_digest = _DownActor()


def test_when_rabbitmq_is_down_the_caller_gets_a_clear_error_and_the_lock_is_given_back(locks):
    down = RabbitJobQueue(locks, _DownActors())
    with pytest.raises(JobQueueUnavailableError, match="not reachable"):
        down.enqueue_build_catalog(1987)
    assert not locks.is_held(lock_keys.CATALOG_BUILD_KEY)  # not stuck: the next try can work

    with pytest.raises(JobQueueUnavailableError):
        down.enqueue_build_digest(3)
    assert not locks.is_held(lock_keys.build_digest_key(3, None))


def test_every_job_has_a_retry_policy_and_a_time_limit():
    for actor in (actors.resolve_upload, actors.fetch_case, actors.build_catalog, actors.refresh_catalog, actors.build_digest):
        assert actor.options["max_retries"] >= 1 and actor.options["time_limit"] >= 15 * 60_000


def test_lawphil_jobs_and_digest_jobs_are_on_separate_queues():
    assert {a.queue_name for a in (actors.resolve_upload, actors.fetch_case, actors.build_catalog, actors.refresh_catalog)} == {LAWPHIL_QUEUE}
    assert actors.build_digest.queue_name == DIGEST_QUEUE
