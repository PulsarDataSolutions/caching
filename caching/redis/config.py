from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from redis import Redis
    from redis.asyncio import Redis as AsyncRedis

OnErrorType = Literal["silent", "raise"]

DEFAULT_KEY_PREFIX = "cache"
DEFAULT_LOCK_TIMEOUT = 10


@dataclass
class RedisConfig:
    """Configuration for Redis cache backend."""

    sync_client: Redis | None
    async_client: AsyncRedis | None
    key_prefix: str
    lock_timeout: int
    on_error: OnErrorType


_redis_config: RedisConfig | None = None


def setup_redis_config(
    sync_client: Redis | None = None,
    async_client: AsyncRedis | None = None,
    key_prefix: str = DEFAULT_KEY_PREFIX,
    lock_timeout: int = DEFAULT_LOCK_TIMEOUT,
    on_error: OnErrorType = "silent",
) -> None:
    """
    Configure the Redis cache backend.

    Must be called before using @redis_cache decorator.
    Can only be called once. Use reset_redis_config() first if reconfiguration is needed.

    Args:
        sync_client: Redis sync client instance (redis.Redis)
        async_client: Redis async client instance (redis.asyncio.Redis)
        key_prefix: Prefix for all cache keys in Redis (default: "cache")
        lock_timeout: Timeout in seconds for distributed locks (default: 10)
        on_error: Error handling mode - "silent" treats errors as cache miss,
                  "raise" propagates exceptions (default: "silent")

    Raises:
        ValueError: If neither sync_client nor async_client is provided
        RuntimeError: If called twice without reset_redis_config() first
    """
    global _redis_config

    if _redis_config is not None:
        raise RuntimeError("Redis config already set. Call reset_redis_config() first if you need to reconfigure.")

    if sync_client is None and async_client is None:
        raise ValueError("At least one of sync_client or async_client must be provided")

    if on_error not in ("silent", "raise"):
        raise ValueError("on_error must be 'silent' or 'raise'")

    _redis_config = RedisConfig(
        sync_client=sync_client,
        async_client=async_client,
        key_prefix=key_prefix,
        lock_timeout=lock_timeout,
        on_error=on_error,
    )


def get_redis_config() -> RedisConfig:
    """
    Get the current Redis configuration.

    Raises:
        RuntimeError: If setup_redis_config() has not been called
    """
    if _redis_config is None:
        raise RuntimeError("Redis not configured. Call setup_redis_config() before using @redis_cache")
    return _redis_config


def reset_redis_config() -> None:
    """
    Reset the Redis configuration to allow reconfiguration.

    Useful for testing or when you need to change Redis connection settings.
    """
    global _redis_config
    _redis_config = None
