from __future__ import annotations

import threading
import time

import pytest

from skimmer.backpressure import AsyncBoundedGate, BoundedGate, Saturated, StaleWork


def test_bounded_gate_allows_up_to_slots_concurrently():
    gate = BoundedGate(slots=2, queue_size=4, max_wait_seconds=1.0)

    gate.acquire()
    gate.acquire()

    # A third caller has to wait -- release from another thread after a short
    # delay so we can observe it queued rather than raising immediately.
    released = threading.Event()

    def release_soon():
        time.sleep(0.05)
        released.set()
        gate.release()

    threading.Thread(target=release_soon).start()

    waited = gate.acquire()
    assert released.is_set()
    assert waited >= 0.04


def test_bounded_gate_raises_saturated_when_queue_is_full():
    gate = BoundedGate(slots=1, queue_size=1, max_wait_seconds=5.0)
    gate.acquire()  # fills the only slot

    # One caller can queue (queue_size=1); park it on a thread so it's really waiting.
    waiter_started = threading.Event()

    def wait_forever():
        waiter_started.set()
        gate.acquire()

    t = threading.Thread(target=wait_forever, daemon=True)
    t.start()
    waiter_started.wait()
    time.sleep(0.05)  # let the waiter actually register itself as queued

    with pytest.raises(Saturated):
        gate.acquire()


def test_bounded_gate_raises_stale_work_after_max_wait():
    gate = BoundedGate(slots=1, queue_size=4, max_wait_seconds=0.05)
    gate.acquire()  # never released within the test

    with pytest.raises(StaleWork):
        gate.acquire()


@pytest.mark.asyncio
async def test_async_bounded_gate_allows_up_to_slots_concurrently():
    gate = AsyncBoundedGate(slots=2, queue_size=4, max_wait_seconds=1.0)

    await gate.acquire()
    await gate.acquire()
    gate.release()

    waited = await gate.acquire()
    assert waited >= 0


@pytest.mark.asyncio
async def test_async_bounded_gate_raises_stale_work_after_max_wait():
    gate = AsyncBoundedGate(slots=1, queue_size=4, max_wait_seconds=0.05)
    await gate.acquire()  # never released within the test

    with pytest.raises(StaleWork):
        await gate.acquire()
