"""Against a REAL RabbitMQ (docker compose up -d rabbitmq). Skipped when it is not running."""
import time
import uuid

import dramatiq
import pytest
from dramatiq import Worker
from dramatiq.brokers.rabbitmq import RabbitmqBroker
from pika.exceptions import AMQPError

from caselens.domain.errors import JobQueueUnavailableError
from caselens.infrastructure.config import Settings
from caselens.infrastructure.queue.broker import build_broker
from caselens.infrastructure.queue.rabbit_job_queue import RabbitJobQueue
from tests.fakes import InMemoryJobLocks

rabbit = pytest.mark.rabbit


@pytest.fixture
def real_broker():
    broker = build_broker(Settings(queue_backend="rabbitmq"))  # the URL in .env / the default
    try:
        broker.connection  # noqa: B018  opens the connection
    except (AMQPError, OSError):
        pytest.skip("RabbitMQ is not running")
    yield broker
    broker.close()


def wait_for(condition, seconds=10.0):
    end = time.time() + seconds
    while time.time() < end:
        if condition():
            return True
        time.sleep(0.05)
    return False


@rabbit
def test_a_job_goes_through_the_real_broker_and_is_run_by_a_worker(real_broker):
    queue_name = f"test-{uuid.uuid4().hex[:8]}"
    seen = []

    @dramatiq.actor(broker=real_broker, queue_name=queue_name)
    def job(value):
        seen.append(value)

    real_broker.declare_actor(job)
    worker = Worker(real_broker, worker_threads=1)
    worker.start()
    try:
        started = time.time()
        job.send("hello")
        assert wait_for(lambda: seen == ["hello"])
        assert time.time() - started < 2  # milliseconds in practice
    finally:
        worker.stop()
        real_broker.delete_queue(queue_name) if hasattr(real_broker, "delete_queue") else None


@rabbit
def test_a_job_that_keeps_failing_is_retried_then_parked_in_the_dead_letter_queue(real_broker):
    queue_name = f"test-{uuid.uuid4().hex[:8]}"
    tries = []

    @dramatiq.actor(broker=real_broker, queue_name=queue_name, max_retries=2, min_backoff=100, max_backoff=200)
    def always_fails():
        tries.append(1)
        raise RuntimeError("boom")

    real_broker.declare_actor(always_fails)
    worker = Worker(real_broker, worker_threads=1)
    worker.start()
    try:
        always_fails.send()
        assert wait_for(lambda: len(tries) == 3, 15)  # the first try and two retries
        time.sleep(0.5)
        dead = real_broker.channel.queue_declare(f"{queue_name}.XQ", passive=True)
        assert dead.method.message_count == 1
    finally:
        worker.stop()


def test_when_rabbitmq_cannot_be_reached_the_real_adapter_gives_a_clear_error_and_frees_the_lock():
    broker = RabbitmqBroker(url="amqp://nobody:nobody@127.0.0.1:1/")  # nothing listens on port 1

    @dramatiq.actor(broker=broker, queue_name="never")
    def job(*args):
        pass

    class Unreachable:
        resolve_upload = fetch_case = build_catalog = refresh_catalog = build_digest = job

    locks = InMemoryJobLocks()
    queue = RabbitJobQueue(locks, Unreachable())
    started = time.time()
    with pytest.raises(JobQueueUnavailableError, match="not reachable"):
        queue.enqueue_build_catalog(1987)
    assert locks.held == set()  # the lock was given back
    assert time.time() - started < 30  # it gives up, it does not hang the request forever
