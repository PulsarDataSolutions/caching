from typing import Callable

from cachify.cache import base_cache
from cachify.redis.lock import RedisLockManager
from cachify.storage.redis_storage import RedisStorage
from cachify.types import CacheConfig, CacheKeyFunction, F, Number

_REDIS_CONFIG = CacheConfig(
    storage=RedisStorage,
    sync_lock=RedisLockManager.sync_lock,
    async_lock=RedisLockManager.async_lock,
    process_isolated=False,
)


def redis_cache(
    ttl: Number = 300,
    never_die: bool = False,
    cache_key_func: CacheKeyFunction | None = None,
    ignore_fields: tuple[str, ...] = (),
) -> Callable[[F], F]:
    """
    Redis cache decorator. See `base_cache` for full documentation.

    Requires setup_redis_config() to be called before use.
    Uses Redis for distributed caching across multiple processes/machines.
    """
    return base_cache(ttl, never_die, cache_key_func, ignore_fields, _REDIS_CONFIG)
