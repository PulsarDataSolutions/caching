"""
Backwards compatibility module.

Redis utilities have been moved to caching.redis.
Storage classes have been moved to caching.storage.
"""

from caching.redis.config import (
    DEFAULT_KEY_PREFIX,
    get_redis_config,
    reset_redis_config,
    setup_redis_config,
)
from caching.redis.lock import RedisLockManager
from caching.storage.memory_storage import CacheEntry, MemoryStorage
from caching.storage.redis_storage import RedisCacheEntry, RedisStorage

__all__ = [
    "CacheEntry",
    "MemoryStorage",
    "RedisCacheEntry",
    "RedisStorage",
    "DEFAULT_KEY_PREFIX",
    "setup_redis_config",
    "get_redis_config",
    "reset_redis_config",
    "RedisLockManager",
]
