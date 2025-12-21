import pickle
import time
from dataclasses import dataclass, field
from typing import Any

from caching.redis.config import get_redis_config
from caching.config import logger
from caching.types import Number


@dataclass
class RedisCacheEntry:
    """Cache entry for Redis storage using Unix timestamps for portability."""

    result: Any
    ttl: float | None

    cached_at: float = field(init=False)
    expires_at: float = field(init=False)

    @classmethod
    def time(cls) -> float:
        return time.time()

    def __post_init__(self):
        self.cached_at = self.time()
        self.expires_at = 0 if self.ttl is None else self.cached_at + self.ttl

    def is_expired(self) -> bool:
        if self.ttl is None:
            return False
        return self.time() > self.expires_at


class RedisStorage:
    """Redis cache storage implementing CacheStorage protocol."""

    @classmethod
    def _make_key(cls, function_id: str, cache_key: str) -> str:
        """Create a Redis key from function_id and cache_key."""
        config = get_redis_config()
        return f"{config.key_prefix}:{function_id}:{cache_key}"

    @classmethod
    def _serialize(cls, entry: RedisCacheEntry) -> bytes:
        """Serialize a cache entry to bytes."""
        try:
            return pickle.dumps(entry, protocol=pickle.HIGHEST_PROTOCOL)
        except (pickle.PicklingError, TypeError, AttributeError) as exc:
            raise TypeError(
                f"Failed to serialize cache entry. Object of type {type(entry.result).__name__} "
                f"cannot be pickled. Ensure the cached result is serializable."
            ) from exc

    @classmethod
    def _deserialize(cls, data: bytes) -> RedisCacheEntry:
        """Deserialize bytes to a cache entry."""
        return pickle.loads(data)

    @classmethod
    def _require_sync_client(cls) -> None:
        """Raise if sync client not configured."""
        config = get_redis_config()
        if config.sync_client is None:
            raise RuntimeError(
                "Redis sync client not configured. "
                "Provide sync_client in setup_redis_config() to use @redis_cache on sync functions."
            )

    @classmethod
    def _require_async_client(cls) -> None:
        """Raise if async client not configured."""
        config = get_redis_config()
        if config.async_client is None:
            raise RuntimeError(
                "Redis async client not configured. "
                "Provide async_client in setup_redis_config() to use @redis_cache on async functions."
            )

    @classmethod
    def set(cls, function_id: str, cache_key: str, result: Any, ttl: Number | None) -> None:
        """Store a result in Redis cache."""
        cls._require_sync_client()
        config = get_redis_config()

        key = cls._make_key(function_id, cache_key)
        entry = RedisCacheEntry(result, ttl)
        data = cls._serialize(entry)

        try:
            if ttl is None:
                config.sync_client.set(key, data)
            else:
                config.sync_client.setex(key, int(ttl) + 1, data)
        except Exception as exc:
            if config.on_error == "raise":
                raise
            logger.debug(f"Redis set error (silent mode): {exc}")

    @classmethod
    def get(cls, function_id: str, cache_key: str, skip_cache: bool) -> RedisCacheEntry | None:
        """Retrieve a cache entry from Redis."""
        if skip_cache:
            return None

        cls._require_sync_client()
        config = get_redis_config()
        key = cls._make_key(function_id, cache_key)

        try:
            data = config.sync_client.get(key)
            if data is None:
                return None

            entry = cls._deserialize(bytes(data))  # type: ignore[arg-type]
            if entry.is_expired():
                return None
            return entry
        except Exception as exc:
            if config.on_error == "raise":
                raise
            logger.debug(f"Redis get error (silent mode): {exc}")
            return None

    @classmethod
    def is_expired(cls, function_id: str, cache_key: str) -> bool:
        """Check if a cache entry is expired or doesn't exist."""
        cls._require_sync_client()
        config = get_redis_config()
        key = cls._make_key(function_id, cache_key)

        try:
            data = config.sync_client.get(key)
            if data is None:
                return True

            entry = cls._deserialize(bytes(data))  # type: ignore[arg-type]
            return entry.is_expired()
        except Exception as exc:
            if config.on_error == "raise":
                raise
            logger.debug(f"Redis is_expired error (silent mode): {exc}")
            return True

    @classmethod
    async def aset(cls, function_id: str, cache_key: str, result: Any, ttl: Number | None) -> None:
        """Store a result in Redis cache (async)."""
        cls._require_async_client()
        config = get_redis_config()

        key = cls._make_key(function_id, cache_key)
        entry = RedisCacheEntry(result, ttl)
        data = cls._serialize(entry)

        try:
            if ttl is None:
                await config.async_client.set(key, data)
            else:
                await config.async_client.setex(key, int(ttl) + 1, data)
        except Exception as exc:
            if config.on_error == "raise":
                raise
            logger.debug(f"Redis aset error (silent mode): {exc}")

    @classmethod
    async def aget(cls, function_id: str, cache_key: str, skip_cache: bool) -> RedisCacheEntry | None:
        """Retrieve a cache entry from Redis (async)."""
        if skip_cache:
            return None

        cls._require_async_client()
        config = get_redis_config()
        key = cls._make_key(function_id, cache_key)

        try:
            data = await config.async_client.get(key)
            if data is None:
                return None

            entry = cls._deserialize(bytes(data))  # type: ignore[arg-type]
            if entry.is_expired():
                return None
            return entry
        except Exception as exc:
            if config.on_error == "raise":
                raise
            logger.debug(f"Redis aget error (silent mode): {exc}")
            return None

    @classmethod
    async def ais_expired(cls, function_id: str, cache_key: str) -> bool:
        """Check if a cache entry is expired or doesn't exist (async)."""
        cls._require_async_client()
        config = get_redis_config()
        key = cls._make_key(function_id, cache_key)

        try:
            data = await config.async_client.get(key)
            if data is None:
                return True

            entry = cls._deserialize(bytes(data))  # type: ignore[arg-type]
            return entry.is_expired()
        except Exception as exc:
            if config.on_error == "raise":
                raise
            logger.debug(f"Redis ais_expired error (silent mode): {exc}")
            return True
