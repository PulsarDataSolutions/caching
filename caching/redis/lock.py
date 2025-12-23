import contextlib
from contextlib import asynccontextmanager, contextmanager
from typing import AsyncIterator, Iterator, Literal, overload
from redis.lock import Lock
from redis.asyncio.lock import Lock as AsyncLock

from caching.redis.config import get_redis_config


class RedisLockManager:
    """Distributed lock manager using Redis locks."""

    @classmethod
    def _make_lock_key(cls, function_id: str, cache_key: str) -> str:
        """Create a Redis lock key."""
        config = get_redis_config()
        return f"{config.key_prefix}:lock:{function_id}:{cache_key}"

    @overload
    @classmethod
    def _get_lock(cls, function_id: str, cache_key: str, is_async: Literal[True]) -> AsyncLock: ...

    @overload
    @classmethod
    def _get_lock(cls, function_id: str, cache_key: str, is_async: Literal[False]) -> Lock: ...

    @classmethod
    def _get_lock(cls, function_id: str, cache_key: str, is_async: bool) -> Lock | AsyncLock:
        """Get client and create lock."""
        config = get_redis_config()
        client = config.get_client(is_async)
        lock_key = cls._make_lock_key(function_id, cache_key)

        return client.lock(lock_key, timeout=config.lock_timeout, blocking=True, blocking_timeout=None)

    @classmethod
    @contextmanager
    def sync_lock(cls, function_id: str, cache_key: str) -> Iterator[None]:
        """
        Acquire a distributed lock for sync operations.

        Uses Redis lock with blocking behavior - waits for lock holder to finish.
        """
        lock: Lock = cls._get_lock(function_id, cache_key, is_async=False)
        acquired = lock.acquire()
        try:
            yield
        finally:
            if not acquired:
                return
            with contextlib.suppress(Exception):
                lock.release()

    @classmethod
    @asynccontextmanager
    async def async_lock(cls, function_id: str, cache_key: str) -> AsyncIterator[None]:
        """
        Acquire a distributed lock for async operations.

        Uses Redis lock with blocking behavior - waits for lock holder to finish.
        """
        lock = cls._get_lock(function_id, cache_key, is_async=True)
        acquired = await lock.acquire()
        try:
            yield
        finally:
            if not acquired:
                return
            with contextlib.suppress(Exception):
                await lock.release()
