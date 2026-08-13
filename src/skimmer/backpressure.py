"""Bounded concurrency gate for the crop-generation path.

Mirrors Beholder's ``BoundedExecutor`` (added in beholder 0.3.1) so both
services shed load the same way under overload: saturation is reported
immediately rather than queuing without limit, and a caller that waited past
``max_wait_seconds`` for a slot is told so rather than served late.

Skimmer's own request-handling concurrency (gunicorn gthreads for Flask, the
asyncio event loop for FastAPI) already *is* the pool of workers -- unlike
Beholder, which needed a pool separate from Vert.x's IO threads to bound
concurrent ffmpeg subprocesses. So there are two gate implementations here,
one per concurrency model, rather than a single worker-pool abstraction:

- ``BoundedGate`` (sync, for Flask): a ``threading.Semaphore`` plus a bounded
  count of waiters.
- ``AsyncBoundedGate`` (async, for FastAPI): the ``asyncio`` equivalent.

Both raise :class:`Saturated` immediately if the waiting queue is already
full, or :class:`StaleWork` if the wait exceeded ``max_wait_seconds``.
"""

from __future__ import annotations

import asyncio
import threading
import time


class Saturated(Exception):
    """Raised immediately when the gate's waiting queue is already full."""


class StaleWork(Exception):
    """Raised when a caller waited longer than max_wait_seconds for a slot."""

    def __init__(self, waited_seconds: float) -> None:
        super().__init__(f"Waited {waited_seconds:.1f}s for a slot")
        self.waited_seconds = waited_seconds


class BoundedGate:
    """Sync (thread-based) bounded concurrency gate, for Flask/gthread workers."""

    def __init__(self, slots: int, queue_size: int, max_wait_seconds: float) -> None:
        if slots <= 0:
            raise ValueError(f"slots must be > 0, got {slots}")
        if queue_size <= 0:
            raise ValueError(f"queue_size must be > 0, got {queue_size}")
        self._semaphore = threading.Semaphore(slots)
        self._queue_size = queue_size
        self._waiting = 0
        self._waiting_lock = threading.Lock()
        self._max_wait_seconds = max_wait_seconds

    def acquire(self) -> float:
        """Reserve a slot, blocking (up to max_wait_seconds) if none is free.

        Returns:
            Seconds waited for the slot.

        Raises:
            Saturated: The waiting queue is already full.
            StaleWork: The wait exceeded max_wait_seconds; no slot was reserved.
        """
        with self._waiting_lock:
            if self._waiting >= self._queue_size:
                raise Saturated
            self._waiting += 1
        try:
            start = time.monotonic()
            timeout = self._max_wait_seconds if self._max_wait_seconds > 0 else None
            acquired = self._semaphore.acquire(timeout=timeout)
            waited = time.monotonic() - start
            if not acquired:
                raise StaleWork(waited)
            return waited
        finally:
            with self._waiting_lock:
                self._waiting -= 1

    def release(self) -> None:
        self._semaphore.release()


class AsyncBoundedGate:
    """Async (asyncio-based) bounded concurrency gate, for FastAPI/uvicorn."""

    def __init__(self, slots: int, queue_size: int, max_wait_seconds: float) -> None:
        if slots <= 0:
            raise ValueError(f"slots must be > 0, got {slots}")
        if queue_size <= 0:
            raise ValueError(f"queue_size must be > 0, got {queue_size}")
        self._semaphore = asyncio.Semaphore(slots)
        self._queue_size = queue_size
        self._waiting = 0
        self._max_wait_seconds = max_wait_seconds

    async def acquire(self) -> float:
        """Async equivalent of :meth:`BoundedGate.acquire`."""
        if self._waiting >= self._queue_size:
            raise Saturated
        self._waiting += 1
        try:
            start = time.monotonic()
            timeout = self._max_wait_seconds if self._max_wait_seconds > 0 else None
            try:
                await asyncio.wait_for(self._semaphore.acquire(), timeout=timeout)
            except TimeoutError:
                raise StaleWork(time.monotonic() - start) from None
            return time.monotonic() - start
        finally:
            self._waiting -= 1

    def release(self) -> None:
        self._semaphore.release()


__all__ = ["AsyncBoundedGate", "BoundedGate", "Saturated", "StaleWork"]
