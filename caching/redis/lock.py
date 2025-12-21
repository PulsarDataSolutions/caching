from contextlib import asynccontextmanager, contextmanager
from typing import AsyncIterator, Iterator

from redis.lock import Lock

from caching.redis.config import get_redis_config


class RedisLockManager:
    """Distributed lock manager using Redis locks."""

    @classmethod
    def _make_lock_key(cls, function_id: str, cache_key: str) -> str:
        """Create a Redis lock key."""
        config = get_redis_config()
        return f"{config.key_prefix}:lock:{function_id}:{cache_key}"

    @classmethod
    @contextmanager
    def sync_lock(cls, function_id: str, cache_key: str) -> Iterator[None]:
        """
        Acquire a distributed lock for sync operations.

        Uses Redis lock with blocking behavior - waits for lock holder to finish.
        """
        config = get_redis_config()

        if config.sync_client is None:
            raise RuntimeError(
                "Redis sync client not configured. "
                "Provide sync_client in setup_redis_config() to use @redis_cache on sync functions."
            )

        lock_key = cls._make_lock_key(function_id, cache_key)
        lock: Lock = config.sync_client.lock(
            lock_key,
            timeout=config.lock_timeout,
            blocking=True,
            blocking_timeout=None,
        )

        acquired = lock.acquire()
        try:
            yield
        finally:
            if not acquired:
                return

            import contextlib

            with contextlib.suppress(Exception):
                lock.release()

    @classmethod
    @asynccontextmanager
    async def async_lock(cls, function_id: str, cache_key: str) -> AsyncIterator[None]:
        """
        Acquire a distributed lock for async operations.

        Uses Redis lock with blocking behavior - waits for lock holder to finish.
        """
        config = get_redis_config()

        if config.async_client is None:
            raise RuntimeError(
                "Redis async client not configured. "
                "Provide async_client in setup_redis_config() to use @redis_cache on async functions."
            )

        lock_key = cls._make_lock_key(function_id, cache_key)
        lock = config.async_client.lock(
            lock_key,
            timeout=config.lock_timeout,
            blocking=True,
            blocking_timeout=None,
        )

        acquired = await lock.acquire()
        try:
            yield
        finally:
            if not acquired:
                return

            import contextlib

            with contextlib.suppress(Exception):
                await lock.release()
