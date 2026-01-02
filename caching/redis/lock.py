import asyncio
import contextlib
import threading
import time
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from typing import AsyncIterator, Iterator, Literal, overload

from redis.lock import Lock
from redis.asyncio.lock import Lock as AsyncLock

from caching.config import logger
from caching.redis.config import get_redis_config

HEARTBEAT_INTERVAL = 1


@dataclass
class _ActiveLockBase:
    """Base class for active lock tracking with shared logic."""

    timeout: float
    last_extended_at: float = field(default_factory=time.monotonic)

    def should_extend(self) -> bool:
        elapsed = time.monotonic() - self.last_extended_at
        return elapsed >= self.timeout / 2

    def mark_extended(self):
        self.last_extended_at = time.monotonic()


@dataclass
class _ActiveAsyncLock(_ActiveLockBase):
    """Tracks an async lock that needs heartbeat extension."""

    lock: AsyncLock = field(kw_only=True)

    async def extend(self) -> bool:
        try:
            await self.lock.extend(self.timeout)
            self.mark_extended()
            return True
        except Exception:
            return False


@dataclass
class _ActiveSyncLock(_ActiveLockBase):
    """Tracks a sync lock that needs heartbeat extension."""

    lock: Lock = field(kw_only=True)

    def extend(self) -> bool:
        try:
            self.lock.extend(self.timeout)
            self.mark_extended()
            return True
        except Exception:
            return False


class _AsyncHeartbeatManager:
    """Manages heartbeat extensions for all async Redis locks."""

    _locks: dict[str, _ActiveAsyncLock] = {}
    _task: asyncio.Task | None = None

    @classmethod
    def register(cls, key: str, lock: AsyncLock, timeout: float):
        cls._locks[key] = _ActiveAsyncLock(timeout=timeout, lock=lock)
        cls._ensure_worker_running()

    @classmethod
    def unregister(cls, key: str):
        cls._locks.pop(key, None)

    @classmethod
    def reset(cls):
        """Cancel worker and clear state. Used for testing cleanup."""
        cls._locks.clear()
        if cls._task is not None and not cls._task.done():
            with contextlib.suppress(RuntimeError):
                cls._task.cancel()
        cls._task = None

    @classmethod
    def _ensure_worker_running(cls):
        if cls._task is None or cls._task.done():
            cls._task = asyncio.create_task(cls._worker())

    @classmethod
    async def _worker(cls):
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL)

            if not cls._locks:
                cls._task = None
                return

            for key, active in list(cls._locks.items()):
                if not active.should_extend():
                    continue
                if not await active.extend():
                    logger.warning(f"Failed to extend lock, it may have expired", extra={"lock_key": key})


class _SyncHeartbeatManager:
    """Manages heartbeat extensions for all sync Redis locks."""

    _locks: dict[str, _ActiveSyncLock] = {}
    _thread: threading.Thread | None = None
    _state_lock: threading.Lock = threading.Lock()

    @classmethod
    def register(cls, key: str, lock: Lock, timeout: float):
        with cls._state_lock:
            cls._locks[key] = _ActiveSyncLock(timeout=timeout, lock=lock)
            cls._ensure_worker_running()

    @classmethod
    def unregister(cls, key: str):
        cls._locks.pop(key, None)

    @classmethod
    def reset(cls):
        """Clear state. Used for testing cleanup. Thread exits on next iteration when _locks is empty."""
        cls._locks.clear()
        cls._thread = None

    @classmethod
    def _ensure_worker_running(cls):
        if cls._thread is None or not cls._thread.is_alive():
            cls._thread = threading.Thread(target=cls._worker, daemon=True)
            cls._thread.start()

    @classmethod
    def _worker(cls):
        while True:
            time.sleep(HEARTBEAT_INTERVAL)

            with cls._state_lock:
                if not cls._locks:
                    cls._thread = None
                    return
                locks_snapshot = list(cls._locks.items())

            for key, active in locks_snapshot:
                if not active.should_extend():
                    continue
                if not active.extend():
                    logger.warning(f"Failed to extend lock, it may have expired", extra={"lock_key": key})


class RedisLockManager:
    """Distributed lock manager using Redis locks."""

    @classmethod
    def _make_lock_key(cls, cache_key: str) -> str:
        """Create a Redis lock key."""
        config = get_redis_config()
        return f"{config.key_prefix}:lock:{cache_key}"

    @overload
    @classmethod
    def _get_lock(cls, cache_key: str, is_async: Literal[True]) -> AsyncLock: ...

    @overload
    @classmethod
    def _get_lock(cls, cache_key: str, is_async: Literal[False]) -> Lock: ...

    @classmethod
    def _get_lock(cls, cache_key: str, is_async: bool) -> Lock | AsyncLock:
        """Get client and create lock."""
        config = get_redis_config()
        client = config.get_client(is_async)
        lock_key = cls._make_lock_key(cache_key)
        return client.lock(
            lock_key,
            timeout=config.lock_timeout,
            blocking=True,
            blocking_timeout=None,
            thread_local=False,  # Required for heartbeat extension from background thread
        )

    @classmethod
    @contextmanager
    def sync_lock(cls, cache_key: str) -> Iterator[None]:
        """
        Acquire a distributed lock for sync operations.

        Uses Redis lock with blocking behavior - waits for lock holder to finish.
        Lock is automatically extended via heartbeat to prevent expiration during long operations.
        """
        config = get_redis_config()
        lock = cls._get_lock(cache_key, is_async=False)
        acquired = False

        try:
            acquired = lock.acquire()
            if acquired:
                _SyncHeartbeatManager.register(lock.name, lock, config.lock_timeout)
                yield
        finally:
            if not acquired:
                return

            _SyncHeartbeatManager.unregister(lock.name)
            with contextlib.suppress(Exception):
                lock.release()

    @classmethod
    @asynccontextmanager
    async def async_lock(cls, cache_key: str) -> AsyncIterator[None]:
        """
        Acquire a distributed lock for async operations.

        Uses Redis lock with blocking behavior - waits for lock holder to finish.
        Lock is automatically extended via heartbeat to prevent expiration during long operations.
        """
        config = get_redis_config()
        lock = cls._get_lock(cache_key, is_async=True)
        acquired = False

        try:
            acquired = await lock.acquire()
            if acquired:
                _AsyncHeartbeatManager.register(lock.name, lock, config.lock_timeout)
                yield
        finally:
            if not acquired:
                return

            _AsyncHeartbeatManager.unregister(lock.name)
            with contextlib.suppress(Exception):
                await lock.release()
