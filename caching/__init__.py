from .features.never_die import clear_never_die_registry
from .memory_cache import cache
from .redis import DEFAULT_KEY_PREFIX, get_redis_config, reset_redis_config, setup_redis_config
from .redis_cache import redis_cache
from .types import CacheKwargs

rcache = redis_cache

__all__ = [
    "cache",
    "rcache",
    "redis_cache",
    "setup_redis_config",
    "get_redis_config",
    "reset_redis_config",
    "DEFAULT_KEY_PREFIX",
    "CacheKwargs",
    "clear_never_die_registry",
]
