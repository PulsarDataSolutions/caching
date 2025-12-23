import pickle
import time
from typing import Any, overload

from caching.redis.config import get_redis_config
from caching.config import logger
from caching.types import CacheEntry, Number


class RedisCacheEntry(CacheEntry):
    @classmethod
    def time(cls) -> float:
        return time.time()


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

    @overload
    @classmethod
    def _prepare_set(cls, function_id: str, cache_key: str, result: Any, ttl: None) -> tuple[str, bytes, None]: ...

    @overload
    @classmethod
    def _prepare_set(cls, function_id: str, cache_key: str, result: Any, ttl: Number) -> tuple[str, bytes, int]: ...

    @classmethod
    def _prepare_set(
        cls, function_id: str, cache_key: str, result: Any, ttl: Number | None
    ) -> tuple[str, bytes, int | None]:
        """Prepare key, data, and expiry in milliseconds for set operations."""
        key = cls._make_key(function_id, cache_key)
        data = cls._serialize(RedisCacheEntry(result, ttl))
        if ttl is None:
            return key, data, None

        return key, data, int(ttl * 1000)

    @classmethod
    def _handle_error(cls, exc: Exception, operation: str):
        """Handle Redis errors based on config."""
        config = get_redis_config()
        if config.on_error == "raise":
            raise

        logger.warning(f"Redis {operation} error (silent mode): {exc}")

    @classmethod
    def _handle_get_result(cls, data: bytes | None) -> RedisCacheEntry | None:
        """Process get result and return entry if valid."""
        if data is None:
            return None

        entry = cls._deserialize(data)
        if entry.is_expired():
            return None

        return entry

    @classmethod
    def set(cls, function_id: str, cache_key: str, result: Any, ttl: Number | None):
        """Store a result in Redis cache."""
        config = get_redis_config()
        client = config.get_client(is_async=False)
        key, data, expiry_ms = cls._prepare_set(function_id, cache_key, result, ttl)
        try:
            if expiry_ms is None:
                client.set(key, data)
                return

            client.psetex(key, expiry_ms, data)
        except Exception as exc:
            cls._handle_error(exc, "set")

    @classmethod
    def get(cls, function_id: str, cache_key: str, skip_cache: bool) -> RedisCacheEntry | None:
        """Retrieve a cache entry from Redis."""
        if skip_cache:
            return None

        config = get_redis_config()
        client = config.get_client(is_async=False)
        key = cls._make_key(function_id, cache_key)
        try:
            return cls._handle_get_result(client.get(key))  # type: ignore[arg-type]
        except Exception as exc:
            cls._handle_error(exc, "get")
            return None

    @classmethod
    async def aset(cls, function_id: str, cache_key: str, result: Any, ttl: Number | None):
        """Store a result in Redis cache (async)."""
        config = get_redis_config()
        client = config.get_client(is_async=True)
        key, data, expiry_ms = cls._prepare_set(function_id, cache_key, result, ttl)
        try:
            if expiry_ms is None:
                await client.set(key, data)
                return

            await client.psetex(key, expiry_ms, data)
        except Exception as exc:
            cls._handle_error(exc, "aset")

    @classmethod
    async def aget(cls, function_id: str, cache_key: str, skip_cache: bool) -> RedisCacheEntry | None:
        """Retrieve a cache entry from Redis (async)."""
        if skip_cache:
            return None

        config = get_redis_config()
        client = config.get_client(is_async=True)
        key = cls._make_key(function_id, cache_key)
        try:
            return cls._handle_get_result(await client.get(key))  # type: ignore[arg-type]
        except Exception as exc:
            cls._handle_error(exc, "aget")
            return None
