"""The locks on real PostgreSQL (migration 0007), including two connections racing for the same key."""
import threading
import time

import pytest
from sqlalchemy import text

from caselens.infrastructure.db.job_lock_repository import SqlJobLockRepository

pytestmark = pytest.mark.db


@pytest.fixture
def locks(test_engine):
    repo = SqlJobLockRepository(test_engine)
    yield repo
    with test_engine.begin() as connection:  # these locks commit for real, so clean up after ourselves
        connection.execute(text("DELETE FROM job_locks WHERE key LIKE 'test:%'"))


def test_a_free_lock_is_taken_and_a_second_taker_is_refused(locks):
    assert locks.acquire("test:a", 60) is True
    assert locks.acquire("test:a", 60) is False
    assert locks.is_held("test:a") is True


def test_a_released_lock_can_be_taken_again(locks):
    locks.acquire("test:b", 60)
    locks.release("test:b")
    assert locks.is_held("test:b") is False
    assert locks.acquire("test:b", 60) is True


def test_different_keys_do_not_block_each_other(locks):
    assert locks.acquire("test:c1", 60) and locks.acquire("test:c2", 60)


def test_a_lock_whose_time_ran_out_is_free_again_so_a_crashed_worker_cannot_block_it_forever(locks):
    assert locks.acquire("test:d", 1) is True
    time.sleep(1.2)
    assert locks.is_held("test:d") is False
    assert locks.acquire("test:d", 60) is True


def test_releasing_a_lock_nobody_holds_is_harmless(locks):
    locks.release("test:nobody")


def test_exactly_one_of_many_racing_connections_gets_the_lock(locks):
    winners, barrier = [], threading.Barrier(8)

    def race():
        barrier.wait()
        winners.append(locks.acquire("test:race", 60))

    threads = [threading.Thread(target=race) for _ in range(8)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert winners.count(True) == 1 and winners.count(False) == 7
